"""Fixed HTTPS endpoint, no redirects and bounded responses."""
import json
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError
from credentials import validate, SetupError

ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
MAX_RESPONSE = 1024000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirect refused', headers, fp)


def ask(payload, key):
    key = validate(key)
    request = Request(ENDPOINT, data=json.dumps(payload).encode(),
                      headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'})
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        body = response.read(MAX_RESPONSE + 1)
    if len(body) > MAX_RESPONSE: raise SetupError('JEV response exceeded the size limit.')
    return json.loads(body)
