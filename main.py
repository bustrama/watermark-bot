import logging
import os
import sys
from functools import wraps
from io import BytesIO

from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from telegram import Update, InputFile
from telegram.ext import MessageHandler, CallbackContext, ApplicationBuilder, AIORateLimiter, ContextTypes, filters

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    stream=sys.stdout,
    level=logging.INFO
)

load_dotenv()

# Replace with your bot token
TOKEN = os.getenv('TELEGRAM_TOKEN')
WHITELIST_CHATS = os.getenv('WHITELIST_CHATS', [])
if isinstance(WHITELIST_CHATS, str):
    WHITELIST_CHATS = [int(id_number) for id_number in WHITELIST_CHATS.split(';')]


def protected(func):
    @wraps(func)
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(WHITELIST_CHATS) > 0 and update.effective_chat.id not in WHITELIST_CHATS:
            await update.message.reply_text('🖕')
            return None
        return await func(update, context)

    return inner


@protected
async def process_pdf(update: Update, context: CallbackContext):
    try:
        text = update.message.caption
        if text is None:
            await update.message.reply_text('watermark text is missing')
            return

        logging.info('process_pdf:: loading file')
        message = await update.message.reply_text('Loading file...')
        file = await update.message.document.get_file()

        file_bytes = BytesIO()
        await file.download_to_memory(file_bytes)
        file_bytes.seek(0)

        # Create watermark
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.translate(inch, inch)
        pdf.setFillColor(colors.grey, alpha=0.2)
        pdf.setFont("Helvetica", 60)
        pdf.rotate(45)
        pdf.drawCentredString(400, 100, text)
        pdf.save()

        watermark_pdf = PdfReader(buffer)
        watermark_page = watermark_pdf.get_page(0)

        # Open the PDF file
        input_pdf = PdfReader(file_bytes)
        pdf_writer = PdfWriter()

        logging.info('process_pdf:: working on pages')
        for i in range(input_pdf.get_num_pages()):
            pdf_page = input_pdf.get_page(i)
            pdf_page.merge_page(watermark_page, over=True)
            pdf_writer.add_page(pdf_page)

        # Set the password for the output PDF
        # logging.info('process_pdf:: locking file')
        # await message.edit_text('Locking file...')
        # pdf_writer.encrypt(text)

        buf = BytesIO()
        pdf_writer.write_stream(buf)
        buf.seek(0)

        # Send the watermarked and password-protected PDF back to the user
        finished_file = InputFile(buf, update.message.document.file_name)
        await context.bot.send_document(chat_id=update.effective_chat.id, document=finished_file)
        await message.delete()
    except:
        await update.message.reply_text('An error has occurred')


def main():
    app = ApplicationBuilder().token(TOKEN).rate_limiter(AIORateLimiter(max_retries=5)).build()

    app.add_handler(MessageHandler(filters.Document.PDF, process_pdf))

    app.run_polling()


if __name__ == '__main__':
    main()
