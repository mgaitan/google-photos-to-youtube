import collections.abc
import getpass
import http.client as httplib
import json
import socket
from pathlib import Path

from IPython.display import Markdown, display

import apiclient.http
import googleapiclient.errors
import httplib2
import ipywidgets as widgets
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


def create_client_id():
    file = Path("client_id.json")
    if file.exists():
        print("file already exists")
        return
    client_id = input("CLIENT_ID: ")
    client_secret = getpass.getpass(prompt="CLIENT_SECRET: ")

    content = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://www.googleapis.com/oauth2/v3/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }
    file.write_text(json.dumps(content, indent=2))


def login(service):
    scopes = {
        "photos": [
            "https://www.googleapis.com/auth/photoslibrary",
            "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata",
            "https://www.googleapis.com/auth/photoslibrary.sharing",
        ],
        "youtube": ["https://www.googleapis.com/auth/youtube.upload"],
    }

    # Create the flow using the client secrets file from the Google API

    flow = Flow.from_client_secrets_file(
        "client_id.json",
        scopes=scopes[service],
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt="consent")

    print("Please go to this URL: {}".format(auth_url))

    # The user will get an authorization code. This code is used to get the
    # access token.
    code = input("Enter the authorization code: ")
    flow.fetch_token(code=code)

    if service == "youtube":

        return build("youtube", "v3", credentials=flow.credentials)
    else:
        return AuthorizedSession(flow.credentials)


def create_db_image(session, album_id):
    data = Path("db_image.webp").read_bytes()
    result = session.post(
        "https://photoslibrary.googleapis.com/v1/uploads",
        data,
        headers={
            "Content-type": "application/octet-stream",
            "X-Goog-Upload-Content-Type": "image/webp",
            "X-Goog-Upload-Protocol": "raw",
        },
    )
    token = result.content.decode()

    payload = {
        "newMediaItems": [
            {"description": "{}", "simpleMediaItem": {"uploadToken": token}}
        ],
    }
    if album_id:
        payload["albumId"] = album_id

    response = session.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate", json=payload
    )

    return response.json()["newMediaItemResults"][0]["mediaItem"]


class DB(collections.abc.MutableMapping):
    """
    A Borg (shared state) dict-like object to permanently store already migrated videos. 
    It maps gphoto url to youtube urls. 

    It's stored as a json blob in the description of the first item of the
    album "migrated-to-youtube" that's created if needed.

    This is a workaround to the limitations of the Goole Photos API
    that doesn't allow to delete or update the description of items that weren't 
    created by the app, nor add them to a custom album. 
    """
    _shared_state = {}  

    def __init__(self, session):
        self.__dict__ = self._shared_state
        if not self._shared_state:
            self.session = session
            self.item = self._get_or_create_db()
            self.data = json.loads(self.item.get("description", "{}"))

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self._commit()

    def __delitem__(self, key):
        del self.data[key]
        self._commit()
    
    def __len__(self):
        return len(self.data)

    def __iter__(self):
        yield from self.data

    def _commit(self):
        self.session.patch(
            f"https://photoslibrary.googleapis.com/v1/mediaItems/{self.item['id']}?updateMask=description",
            json={"description": json.dumps(self.data, indent=2)},
        )

    def _get_or_create_db(self):
        """
        return the MediaItem dict of the image that's store our db. 
        If the album doesn't exist, it's created and an image is uploaded.
        """
        result = self.session.get(
            "https://photoslibrary.googleapis.com/v1/albums",
            params={"excludeNonAppCreatedData": True},
        )
        for album in result.json().get("albums", []):
            if album["title"] == "migrated-to-youtube":

                result = self.session.post(
                    "https://photoslibrary.googleapis.com/v1/mediaItems:search",
                    json={"albumId": album["id"]},
                )
                return result.json()["mediaItems"][0]
        else:
            album = self.session.post(
                "https://photoslibrary.googleapis.com/v1/albums",
                json={"album": {"title": "migrated-to-youtube"}},
            ).json()
            return create_db_image(self.session, album["id"])

    def _repr_html_(self):
        html = ["<table width=100%>"]
        for key, value in self.items():
            html.append("<tr><th>Google Photos</th><th>Youtube</th></tr>")
            html.append("<tr>")
            html.append("<td>{0}</td>".format(key))
            html.append("<td>{0}</td>".format(value))
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)


def get_videos(session, token=None, page_size=50):
    q = {
        "pageSize": page_size,
        "filters": {"mediaTypeFilter": {"mediaTypes": ["VIDEO"]}},
    }
    if token:
        q["pageToken"] = token
    return session.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:search", json=q
    ).json()


def get_stream(session, video):
    return session.get(f"{video['baseUrl']}=dv", stream=True)


def get_size(session, video):
    return int(
        session.head(f"{video['baseUrl']}=dv", allow_redirects=True).headers[
            "Content-Length"
        ]
    )


DEFAULT_CHUNK_SIZE = 1024 * 1024


def upload_stream(
    youtube,
    stream,
    title,
    description="",
    privacy_status="private",  # "unlisted", "public"
    tags=(),
    progress=None,
):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }
    body_keys = ",".join(body.keys())

    media = MediaStreamUpload(stream)
    request = youtube.videos().insert(part=body_keys, body=body, media_body=media)

    while True:
        status, response = request.next_chunk()
        if status and progress:
            progress.value += DEFAULT_CHUNK_SIZE
        if response:
            progress.value = progress.max
            return f"https://youtu.be/{response['id']}"


# TODO retry when any of this exceptions happen
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
        if self._cursor != begin:
            self._cursor = begin
            self._current_buffer = next(self._iter)
        return self._current_buffer

    def has_stream(self):
        return False  # True

    def to_json(self):
        """This upload type is not serializable."""
        raise NotImplementedError("MediaIoBaseUpload is not serializable.")


def video_block(video, session, youtube):
    title = widgets.Text(
        value=video.get("description", ""),
        description="Title",
        disabled=False,
    )
    title.layout.width = "30em"
    description = widgets.Textarea(
        value="\n - ".join(
            [
                "",
                "Migrado desde Google Photos con http://github.com/mgaitan/google-photos-to-youtube",
                f"Fecha de subida original: {video['mediaMetadata']['creationTime']}",
                f"Google photo ID:  {video['id']}",
                f"Url original:  {video['productUrl']}",
            ]
        ),
        description="Description",
        disabled=False,
    )
    description.layout.height = "6em"
    description.layout.width = "30em"
    privacy = widgets.Dropdown(
        options=["private", "unlisted", "public"],
        value="private",
        description='Privacy status:',
        disabled=False,
    ) 
    privacy.layout.width = "30em"
    tags = widgets.Text(
        value="google-photos-to-youtube, ",
        description="Tags",
        disabled=False,
    )
    tags.layout.width = "30em"
    output = widgets.Output()
    button = widgets.Button(description="Upload to youtube!")

    thumb = Markdown(f"[![]({video['baseUrl']}=w300-h300-no)]({video['productUrl']})")
    display(thumb, title, description, privacy, tags, button, output)

    def on_button_clicked(b):
        video_title = title.value.strip()
        if not video_title:
            title.placeholder = "Enter a title"
            title.focus()
            return

        with output:
            bar = widgets.IntProgress(
                value=0,
                min=0,
                max=get_size(session, video),
                description="Uploading:",
                bar_style="info",
                orientation="horizontal",
            )
            display(bar)
            stream = get_stream(session, video)
            response = upload_stream(
                youtube,
                stream,
                title=video_title,
                description=description.value,
                tags=[t.strip() for t in tags.value.split(",")],
                privacy_status=privacy.value,
                progress=bar,
            )
            print(response)

            # update DB
            db = DB(session)
            db[video["productUrl"]] = response

    button.on_click(on_button_clicked)


def load_page(session, youtube, token=None):
    db = DB(session)
    videos = get_videos(session, token)
    for video in videos["mediaItems"]:
        item_url = video["productUrl"]
        if item_url not in db:
            video_block(video, session, youtube)

    button = widgets.Button(description="Load more...")
    output = widgets.Output()

    def next_page(b):
        button.close()
        with output:
            load_page(session, youtube, token=videos["nextPageToken"])

    button.on_click(next_page)
    display(output, button)
