#!/usr/bin/env python3
import cgi
import io
import json
import logging
from os.path import join

import requests
from flask import jsonify, Response, make_response, send_file
from privex.helpers import empty
from privex.steemengine import Token
from privex.steemengine.exceptions import TokenNotFound

from core import flask, get_redis, cf, get_steemengine, BASE_DIR

log = logging.getLogger('imageproxy')

rq = requests.Session()


def get_token(symbol: str) -> Token:
    """Get the token metadata for a given symbol, and cache it in Redis for CACHE_TIME"""
    symbol = symbol.strip().upper()
    if len(symbol) > 20:
        raise AttributeError('Symbol is too long...')
    rkey = f'stkn:{symbol}'
    r = get_redis()
    res = r.get(rkey)

    if empty(res):
        res = get_steemengine().get_token(symbol)
        if empty(res):
            raise TokenNotFound(f"Symbol '{symbol}' was not found on SteemEngine.")
        res = dict(res)
        r.set(rkey, json.dumps(res), ex=cf['CACHE_TIME'])
    else:
        res = json.loads(res)

    return Token(**res)


@flask.route('/')
def index():
    return jsonify(error=False, name="Privex SteemEngine Token Image Proxy", version="1.0")


@flask.route('/token/<sym>')
def token_data(sym):
    try:
        st = get_token(sym)
        return jsonify(error=False, result=dict(st))
    except AttributeError:
        log.debug("Symbol '%s' was too long.", sym)
        return jsonify(error=True, message="Symbol is too long. Refusing to look up."), 400
    except TokenNotFound as e:
        return jsonify(error=True, message=str(e)), 400


@flask.route('/token/<sym>/icon')
def token_icon(sym):
    try:
        st = get_token(sym)
        url = st.metadata.icon
        log.debug('Downloading icon for %s from url: %s', sym, url)
        usplit = url.split('.')
        uext = usplit[-1].lower().strip()
        image = rq.get(url=url, timeout=10, stream=True)
        h = image.headers
        if uext in ['jpg', 'jpeg', 'png', 'tiff', 'svg', 'gif', 'webm', 'webp']:
            ext = uext
        else:
            # Parse the content disposition to get the filename for the download
            v, disp = cgi.parse_header(h.get('Content-Disposition', 'attachment; filename=image.png'))
            filename = disp['filename']
            ext = filename.split('.')[-1]
            # mime = 'image/svg+xml' if ext == 'svg' else 'image/' + ext
        mime = h.get('Content-Type', 'image/svg+xml' if ext == 'svg' else 'image/' + ext)
        save_file = join(BASE_DIR, 'static', 'icons', '.'.join([sym, ext]))
        with open(save_file, 'wb') as f:
            image.raw.decode_content = True
            for chunk in image:
                f.write(chunk)

        with open(save_file, 'rb') as f:
            fdata = io.BytesIO(f.read())
            return send_file(fdata, mimetype=mime, as_attachment=False, attachment_filename='icon.' + ext)
    except AttributeError:
        log.debug("Symbol '%s' was too long.", sym)
        return jsonify(error=True, message="Symbol is too long. Refusing to look up."), 400
    except TokenNotFound as e:
        return jsonify(error=True, message=str(e)), 400


if __name__ == "__main__":
    flask.run(debug=cf['DEBUG'])
