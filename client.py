import json
import os
import requests
import gettext.gettext as _

__author__ = 'thlu79@gmail.com'

API_BASE_URL = os.environ.get('SWISH_API_BASE_URL', 'https://swicpc.bgc.se/api/v1/')
ERROR_CODES = {
    'FF08': _("PayeePaymentReference is invalid"),
    'RP03': _("Callback URL is missing or does not use Https"),
    'BE18': _("Payer alias is invalid"),
    'RP01': _("Payee alias is missing or empty"),
    'PA02': _("Amount value is missing or not a valid number"),
    'AM06': _("Amount value is too low"),
    'AM02': _("Amount value is too large"),
    'AM03': _("Invalid or missing Currency"),
    'RP02': _("Invalid Message text"),
    'RP06': _("Another active PaymentRequest already exists for this payerAlias"),
    'ACMT03': _("Payer not Enrolled"),
    'ACMT01': _("Payer is not activated"),
    'ACMT07': _("Payee not Enrolled"),
}

class SwishError(Exception):
    def __init__(self, message, error_objects):
        super(SwishError, self).__init__(message)
        self.error_objects = error_objects


class SwishHttpError(Exception):
    def __init__(self, message, response):
        super(SwishError, self).__init__(message)
        self.response = response


class SwishResponse(object):
    def __init__(self, location, token):
        self.location = location
        self.token = token
        self.id = self.location.split('/')[-1] if self.location else None


class SwishClient(object):
    def __init__(self, payee_alias, api_base_url=None):
        self.payee_alias = payee_alias
        self.api_base_url = API_BASE_URL if api_base_url is None else api_base_url


    def post(self, endpoint, json, **kwargs):
        r = requests.post(self.api_base_url + endpoint, json=json,
                          headers={'Content-Type': 'application/json'},
                          **kwargs)
        return r

    def payment_request(self,
                        reference,
                        payer_alias,
                        amount,
                        callback_url=None,
                        currency='SEK',
                        message='',
                        payee_alias=None,
                        ):
        json_data = {
            'payeePaymentReference': reference,
            'callbackUrl': callback_url,
            'payerAlias': payer_alias,
            'payeeAlias': self.payee_alias if payee_alias is None else payee_alias,
            'amount': str(amount).replace('.', ','),
            'currency': currency,
            'message': message,
        }
        json_str = json.dumps(json_data)
        r = self.post('paymentrequests', json_str)
        if r.status_code == 201:
            # Created OK
            return SwishResponse(r.headers['location'], None)
        elif r.status_code == 422:
            raise SwishError("Unprocessable entity", r.json())
        raise SwishHttpError("HTTP Error", r)

    def refund(self,
               reference,
               original_id,
               payer_alias,
               amount,
               callback_url=None,
               currency='SEK',
               message=''
               ):
        data = {
            'payerPaymentReference': reference,
            'originalPaymentReference': original_id,
            'callbackUrl': callback_url,
            'payerAlias': payer_alias,
            'amount': amount,
            'currency': currency,
            'message': message,
        }
        r = self.post('refunds', json.dumps(data))
        if r.status_code == 201:
            # Refund OK
            return SwishResponse(r.headers['location'], None)
        elif r.status_code == 422:
            raise SwishError("Unprocessable entity", r.json())
        raise SwishHttpError("HTTP Error", r)

    def status(self, location):
        """Get status of either payment or refund.
        Use location from SwishResponse
        Returns: Dictionary from JSON response
        """
        r = requests.get(location)
        if r.status_code == 200:
            return r.json()
        raise SwishHttpError("HTTP Error", r)
