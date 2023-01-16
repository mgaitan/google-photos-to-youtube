[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb)

Google Photos is expensive and Youtube is free. Why not move my videos there (using their bandwidth and resources for more pleasure)?

## How it works

It searches videos using the Google Photos api in your account and display a thumbnail of each one. Then you can complete some metadata and upload it to the same or different Youtube account. 
The uploading process is done in chunks, so it doesn't require to download the full video to start uploading it. 


## Setup

1. Follow https://developers.google.com/photos/library/guides/get-started to create a new project (as a "Desktop app" could work). Remember to copy `CLIENT_ID` and `CLIENT_SECRET` of your app.


2. In addition to Google Photos, your app requires access `Youtube data v3 API`. Enable it from https://console.cloud.google.com/apis/dashboard clicking in "Enable APIS and SERVICES"


3. As your app will be in "Testing" mode, you need to authorize the specific accounts that will use the app. Goto to https://console.cloud.google.com/apis/credentials/consent and add them clicking in "Add user". It could be more than one account as the source Google Photos account and the Youtube account could be differents. 

4. Open [the notebook](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb) in Colab, run the cells and follow the instructions. 


