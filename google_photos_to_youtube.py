import functools
import http.client as httplib
import socket

from IPython.display import Markdown, display

import apiclient.http
import googleapiclient.errors
import httplib2
import ipywidgets as widgets
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


def login(service):
    scopes = {
        "photos": [
            "https://www.googleapis.com/auth/photoslibrary",
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


@functools.cache
def get_or_create_album(session):
    result = session.get(
        "https://photoslibrary.googleapis.com/v1/albums",
        params={"excludeNonAppCreatedData": True},
    )

    for album in result.json().get("albums", []):
        if album["title"] == "migrated-to-youtube":
            return album["id"]
    else:
        response = session.post(
            "https://photoslibrary.googleapis.com/v1/albums",
            json={"album": {"title": "migrated-to-youtube"}},
        )
        return response.json()["id"]


def add_to_album(session, item_id):
    album_id = get_or_create_album(session)
    return session.post(
        f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:batchAddMediaItems",
        json={"mediaItemIds": [item_id]},
    )
    


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
        value=video.get("description", video.get("id")),
        description="Title",
        disabled=False,
    )
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
    tags = widgets.Text(
        value="google-photos-to-youtube, ",
        placeholder="from-google-photos",
        description="Tags",
        disabled=False,
    )
    output = widgets.Output()
    button = widgets.Button(description="Upload to youtube!")

    thumb = Markdown(f"[![]({video['baseUrl']}=w300-h300-no)]({video['productUrl']})")
    display(thumb, title, description, tags, button, output)

    def on_button_clicked(b):
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
                title=title.value,
                description=description.value,
                tags=[t.strip() for t in tags.value.split(",")],
                progress=bar,
            )
            print(response)

            # this approach is not working due API limitations 
            # see https://stackoverflow.com/a/56897605
            # add_to_album(session, video["id"])
            
    button.on_click(on_button_clicked)


def load_page(session, youtube, token=None):

    videos = get_videos(session, token)
    for video in videos["mediaItems"]:
        video_block(video, session, youtube)

    button = widgets.Button(description="Load more...")
    output = widgets.Output()

    def next_page(b):
        button.close()
        with output:
            load_page(session, youtube, token=videos["nextPageToken"])
    
    button.on_click(next_page)
    display(output, button)
