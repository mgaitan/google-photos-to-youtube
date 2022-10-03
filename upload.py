import argparse
import http.client as httplib
import json
import logging
import random
import socket
import time

import apiclient.http
import googleapiclient.errors
import httplib2
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from google_auth_oauthlib.flow import InstalledAppFlow


def retriable_exceptions(fun, retriable_exceptions, max_retries=None):
    """Run function and retry on some exceptions (with exponential backoff)."""
    retry = 0
    while 1:
        try:
            return fun()
        except tuple(retriable_exceptions) as exc:
            retry += 1
            if type(exc) not in retriable_exceptions:
                raise exc
            # we want to retry 5xx errors only
            elif (
                type(exc) == googleapiclient.errors.HttpError and exc.resp.status < 500
            ):
                raise exc
            elif max_retries is not None and retry > max_retries:
                logging.error("[Retryable errors] Retry limit reached")
                raise exc
            else:
                seconds = random.uniform(0, 2**retry)
                message = (
                    "[Retryable error {current_retry}/{total_retries}] "
                    + "{error_type} ({error_msg}). Wait {wait_time} seconds"
                ).format(
                    current_retry=retry,
                    total_retries=max_retries or "-",
                    error_type=type(exc).__name__,
                    error_msg=str(exc) or "-",
                    wait_time="%.1f" % seconds,
                )
                logging.debug(message)
                time.sleep(seconds)


def parse_args(arg_input=None):
    parser = argparse.ArgumentParser(description="Upload photos to Google Photos.")
    parser.add_argument("--video")
    parser.add_argument(
        "--log",
        metavar="log_file",
        dest="log_file",
        help="name of output file for log messages",
    )

    return parser.parse_args(arg_input)


def auth(scopes):
    flow = InstalledAppFlow.from_client_secrets_file("client_id.json", scopes=scopes)

    credentials = flow.run_local_server(
        host="localhost",
        port=8080,
        authorization_prompt_message="",
        success_message="The auth flow is complete; you may close this window.",
        open_browser=True,
    )

    return credentials


def get_authorized_sessions(auth_token_file):

    scopes_photos = [
        "https://www.googleapis.com/auth/photoslibrary",
        "https://www.googleapis.com/auth/photoslibrary.sharing",
    ]
    scopes_yt = ["https://www.googleapis.com/auth/youtube.upload"]

    # TODO allow different sessions for source (photos) and target (yt)
    scopes = scopes_photos + scopes_yt
    cred = None

    if auth_token_file:
        try:
            cred = Credentials.from_authorized_user_file(auth_token_file, scopes)
        except OSError as err:
            logging.debug(f"Error opening auth token file - {err}")
        except ValueError:
            logging.debug("Error loading auth tokens - Incorrect format")

    if not cred:
        cred = auth(scopes)

    session = AuthorizedSession(cred)
    youtube = build("youtube", "v3", credentials=cred)

    if auth_token_file:
        try:
            save_cred(cred, auth_token_file)
        except OSError as err:
            logging.debug(f"Could not save auth tokens - {err}")

    return session, youtube


def save_cred(cred, auth_file):

    cred_dict = {
        "token": cred.token,
        "refresh_token": cred.refresh_token,
        "id_token": cred.id_token,
        "scopes": cred.scopes,
        "token_uri": cred.token_uri,
        "client_id": cred.client_id,
        "client_secret": cred.client_secret,
    }

    with open(auth_file, "w") as f:
        print(json.dumps(cred_dict), file=f)


def get_videos(session):
    q = {"filters": {"mediaTypeFilter": {"mediaTypes": ["VIDEO"]}}}
    return session.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:search", json=q
    ).json()


def upload(
    youtube,
    file,
    title,
    description="",
    tags=(),
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
        },
        "status": {
            "privacyStatus": "unlisted",  # "private", "public"
        },
    }
    body_keys = ",".join(body.keys())

    media = apiclient.http.MediaFileUpload(
        file, chunksize=-1, resumable=True, mimetype="application/octet-stream"
    )
    request = youtube.videos().insert(part=body_keys, body=body, media_body=media)
    status, response = request.next_chunk()
    return status, response


def upload_stream(
    youtube,
    stream,
    title,
    description="",
    tags=(),
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
        },
        "status": {
            "privacyStatus": "unlisted",  # "private", "public"
        },
    }
    body_keys = ",".join(body.keys())

    media = MediaStreamUpload(stream)
    request = youtube.videos().insert(part=body_keys, body=body, media_body=media)

    while True:
        status, response = request.next_chunk()
        if status:
            print("status: ", status)
        if response:
            return response


RETRIABLE_EXCEPTIONS = [
    socket.error,
    IOError,
    httplib2.HttpLib2Error,
    httplib.NotConnected,
    httplib.IncompleteRead,
    httplib.ImproperConnectionState,
    httplib.CannotSendRequest,
    httplib.CannotSendHeader,
    httplib.ResponseNotReady,
    httplib.BadStatusLine,
    googleapiclient.errors.HttpError,
]


DEFAULT_CHUNK_SIZE = 1024 * 1024


class MediaStreamUpload(apiclient.http.MediaUpload):
    def __init__(self, stream, chunksize=DEFAULT_CHUNK_SIZE, resumable=True):

        super(MediaStreamUpload, self).__init__()

        self._stream = stream
        self._mimetype = stream.headers["content-type"]
        self._resumable = resumable
        if not (chunksize == -1 or chunksize > 0):
            raise ValueError("invalid chunksize error")
        self._chunksize = chunksize
        self._size = int(stream.headers["Content-Length"])

        self._iter = stream.iter_content(chunk_size=chunksize)
        self._cursor = None
        self._current_buffer = b""

    def chunksize(self):
        return self._chunksize

    def mimetype(self):
        return self._mimetype

    def size(self):
        return self._size

    def resumable(self):
        return self._resumable

    def getbytes(self, begin, length):
        import ipdb

        ipdb.set_trace()
        print(f"{begin} - {length}")
        if self._cursor != begin:
            self._cursor = begin
            self._current_buffer = next(self._iter)
        return self._current_buffer

    def has_stream(self):
        return False    # True

    def to_json(self):
        """This upload type is not serializable."""
        raise NotImplementedError("MediaIoBaseUpload is not serializable.")


def main():

    args = parse_args()

    logging.basicConfig(
        format="%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s",
        datefmt="%m/%d/%Y %I_%M_%S %p",
        filename=args.log_file,
        level=logging.INFO,
    )

    session, youtube = get_authorized_sessions("token.json")

    videos = get_videos(session)

    v = videos["mediaItems"][0]    # [1]
    print(v)
    stream = session.get(f"{v['baseUrl']}=dv", stream=True)
    response = upload_stream(
        youtube, stream, title="[test] google photos 2 youtube"
    )
    print(response)


if __name__ == "__main__":
    main()
