import io
import os
import cv2
from deep_translator import GoogleTranslator
from langdetect import DetectorFactory, detect
import numpy as np
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import PyPDF2
import pytesseract

# Deterministic language detection
DetectorFactory.seed = 0

# Configure paths for Windows
pytesseract.pytesseract.tesseract_cmd = (
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)
poppler_path = r'C:\Program Files\poppler-25.12.0\Library\bin'


def is_pdf_searchable(input_path):
  """Checks if the PDF already contains selectable text."""
  try:
    reader = PyPDF2.PdfReader(input_path)
    extracted_text = ''
    for page in reader.pages:
      text = page.extract_text()
      if text:
        extracted_text += text.strip()
    return len(extracted_text) > 20, extracted_text
  except Exception:
    return False, ''


def detect_language(text):
  """Detects language of given text."""
  try:
    if not text or len(text.strip()) < 5:
      return 'en'
    return detect(text)
  except Exception:
    return 'en'


def translate_text(text, source_lang='auto', target_lang='en'):
  """Translates a block or string of text."""
  if not text or not text.strip():
    return ''
  try:
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    return translator.translate(text)
  except Exception:
    return text


def process_image_in_place_translation(
    pil_img, source_lang='es', target_lang='en'
):
  """Replaces non-English text on image bounding boxes while preserving layout,

  background colors, and styling.
  """
  open_cv_image = np.array(pil_img)
  open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

  # FIXED: Fallback to default engine if language data file is missing
  try:
    ocr_data = pytesseract.image_to_data(
        pil_img, lang=source_lang, output_type=pytesseract.Output.DICT
    )
  except pytesseract.TesseractError:
    # Use default OCR layout detector if specific language pack isn't installed in Tesseract
    ocr_data = pytesseract.image_to_data(
        pil_img, output_type=pytesseract.Output.DICT
    )

  n_boxes = len(ocr_data['text'])
  result_image = pil_img.copy()
  draw = ImageDraw.Draw(result_image)

  # Group words into blocks/lines
  blocks = {}
  for i in range(n_boxes):
    text = ocr_data['text'][i].strip()
    conf = int(ocr_data['conf'][i])

    if conf > 15 and text:
      block_num = ocr_data['block_num'][i]
      line_num = ocr_data['line_num'][i]
      key = (block_num, line_num)

      if key not in blocks:
        blocks[key] = {
            'text': [text],
            'left': ocr_data['left'][i],
            'top': ocr_data['top'][i],
            'right': ocr_data['left'][i] + ocr_data['width'][i],
            'bottom': ocr_data['top'][i] + ocr_data['height'][i],
        }
      else:
        blocks[key]['text'].append(text)
        blocks[key]['right'] = max(
            blocks[key]['right'], ocr_data['left'][i] + ocr_data['width'][i]
        )
        blocks[key]['bottom'] = max(
            blocks[key]['bottom'], ocr_data['top'][i] + ocr_data['height'][i]
        )

  # Process each block
  for key, b in blocks.items():
    original_line = ' '.join(b['text'])
    if not original_line.strip():
      continue

    translated_line = translate_text(
        original_line, source_lang=source_lang, target_lang=target_lang
    )

    x, y = b['left'], b['top']
    w = b['right'] - b['left']
    h = b['bottom'] - b['top']

    # Sample surrounding background color
    crop_bg = open_cv_image[
        max(0, y - 2) : min(open_cv_image.shape[0], y + 2),
        max(0, x - 2) : min(open_cv_image.shape[1], x + 2),
    ]

    if crop_bg.size > 0:
      bg_color_bgr = np.mean(crop_bg, axis=(0, 1)).astype(int)
      bg_color_rgb = (
          int(bg_color_bgr[2]),
          int(bg_color_bgr[1]),
          int(bg_color_bgr[0]),
      )
    else:
      bg_color_rgb = (255, 255, 255)

    # Erase original text area
    draw.rectangle([x - 2, y - 2, x + w + 2, y + h + 2], fill=bg_color_rgb)

    # Calculate contrast text color (White or Black)
    bg_luminance = (
        0.299 * bg_color_rgb[0]
        + 0.587 * bg_color_rgb[1]
        + 0.114 * bg_color_rgb[2]
    )
    text_color = (255, 255, 255) if bg_luminance < 128 else (0, 0, 0)

    # Approximate font size
    font_size = max(12, int(h * 0.75))
    try:
      font = ImageFont.truetype('arial.ttf', font_size)
    except OSError:
      font = ImageFont.load_default()

    draw.text((x, y), translated_line, fill=text_color, font=font)

  return result_image


def process_single_pdf(input_path, output_path, dpi=300):
  """Processes PDF file preserving layout."""
  print(f'Processing: {os.path.basename(input_path)}')

  searchable, existing_text = is_pdf_searchable(input_path)

  if searchable:
    print(' -> PDF is searchable.')
    lang = detect_language(existing_text)
    print(f' -> Detected language: {lang}')

    if lang == 'en':
      print(' -> Document is English. Direct copying...')
      with open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
        f_out.write(f_in.read())
      print(f'✓ Completed: {os.path.basename(output_path)}')
      return True

  print(' -> Processing scanned/non-English layout preservation...')
  images = convert_from_path(input_path, dpi=dpi, poppler_path=poppler_path)

  # Check language on sample image
  try:
    sample_text = pytesseract.image_to_string(images[0])
  except Exception:
    sample_text = ''

  detected_lang = detect_language(sample_text)
  print(f' -> OCR Language Detected: {detected_lang}')

  translated_images = []
  for i, img in enumerate(images):
    print(f' -> Translating page {i+1}/{len(images)} in-place...')
    if detected_lang != 'en':
      translated_img = process_image_in_place_translation(
          img, source_lang=detected_lang, target_lang='en'
      )
    else:
      translated_img = img
    translated_images.append(translated_img)

  print(' -> Building final output PDF...')
  pdf_writer = PyPDF2.PdfWriter()

  for img in translated_images:
    p_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='pdf')
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(p_bytes))
    pdf_writer.add_page(pdf_reader.pages[0])

  with open(output_path, 'wb') as f_out:
    pdf_writer.write(f_out)

  print(
      f'✓ Completed (Layout Preserved & Translated):'
      f' {os.path.basename(output_path)}'
  )
  return True


def process_folder(input_folder, output_folder, dpi=300):
  os.makedirs(output_folder, exist_ok=True)
  pdf_files = [
      f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')
  ]

  if not pdf_files:
    print('No PDF files found in input folder!')
    return

  print(f'Found {len(pdf_files)} PDF file(s) to process\n')
  for pdf_file in pdf_files:
    input_path = os.path.join(input_folder, pdf_file)
    output_path = os.path.join(output_folder, pdf_file)
    process_single_pdf(input_path, output_path, dpi)
    print()


if __name__ == '__main__':
  INPUT_FOLDER = 'input'
  OUTPUT_FOLDER = 'output'
  DPI = 300
  process_folder(INPUT_FOLDER, OUTPUT_FOLDER, DPI)