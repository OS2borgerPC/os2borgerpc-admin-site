from django.conf import settings

def iso_urls(request):
    """
    Adds PC and Kiosk ISO URLs to the context for all templates.
    """
    return {
        "pc_image_releases_url": getattr(settings, "PC_IMAGE_RELEASES_URL", ""),
        "kiosk_image_releases_url": getattr(settings, "KIOSK_IMAGE_RELEASES_URL", ""),
    }