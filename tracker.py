#Phone number location

import phonenumbers
from phonenumbers import geocoder

phone_number = phonenumbers.parse("+254700892264")

print(geocoder.description_for_number(phone_number, "en"))
