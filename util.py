from django.conf import settings
import hmac

def calc_url_mac(url, position, recipient, timestamp):
	mash = ''.join([str(url), str(position), str(recipient), str(timestamp)])
	return hmac.new(settings.SECRET_KEY, mash).hexdigest()