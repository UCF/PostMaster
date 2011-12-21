from django.conf import settings
import hmac

def calc_url_mac(url, position, recipient, instance_id):
	mash = ''.join([str(url), str(position), str(recipient), str(instance_id))
	return hmac.new(settings.SECRET_KEY, mash).hexdigest()

def calc_open_mac(recipient, instance_id):
	mash = ''.join([str(recipient), str(instance_id))
	return hmac.new(settings.SECRET_KEY, mash).hexdigest()