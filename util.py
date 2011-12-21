from django.conf import settings
import hmac

def calc_url_mac(url, position, recipient):
	mash = ''.join([str(url), str(position), str(recipient))
	return hmac.new(settings.SECRET_KEY, mash).hexdigest()