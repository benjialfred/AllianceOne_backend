from django.core.management.base import BaseCommand
from django.conf import settings
from platform_services.telegram.client import TelegramClient

class Command(BaseCommand):
    help = "Manage Telegram Webhook for Alliance One (@AllianceOneAIBot)"

    def add_arguments(self, parser):
        parser.add_argument('url', nargs='?', type=str, help='The HTTPS webhook URL to set')
        parser.add_argument('--info', action='store_true', help='Retrieve current webhook status')
        parser.add_argument('--delete', action='store_true', help='Delete the existing webhook')

    def handle(self, *args, **options):
        client = TelegramClient()

        if options['info']:
            self.stdout.write(self.style.NOTICE("Fetching Telegram webhook info..."))
            info = client.get_webhook_info()
            self.stdout.write(self.style.SUCCESS(f"Webhook Info: {info}"))
            return

        if options['delete']:
            self.stdout.write(self.style.WARNING("Deleting Telegram webhook..."))
            res = client.delete_webhook()
            self.stdout.write(self.style.SUCCESS(f"Webhook deleted: {res}"))
            return

        url = options['url']
        if not url:
            self.stdout.write(self.style.ERROR("Please provide a webhook URL or use --info / --delete"))
            return

        secret_token = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
        self.stdout.write(self.style.NOTICE(f"Setting webhook to: {url}"))
        res = client.set_webhook(url=url, secret_token=secret_token)
        self.stdout.write(self.style.SUCCESS(f"Webhook successfully set! Result: {res}"))
