[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb)

Google Photos is expensive and Youtube is free. Why not move my videos there (using their bandwidth and resources for more pleasure)?


## Setup

1. Copy `client_id.json.dist` as `client_id.json`

and follow https://developers.google.com/photos/library/guides/get-started to create a google app. 

It requires permissions on Google Photos and Youtube data v3 APIs to download and upload from one service to the other. 


2. Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` in the client_id.json file with the provided Client ID. 

3. Locally `python google_photos_to_youtube.py` to generate the file `token.json` using the account that own the videos. 

4. Open the notebook in colab uploading `client_id.json` and `token.json` if needed. Alternatively you can run it locally in Jupyter Lab. 


## How it works

It searches videos using the Google photos in your account and display a thumbnail of each one. Then you can complete some metadata and upload it to Youtube. The uploading process is done in chunks, so it doesn't require to download the full video to start uploading it. 



## Acknowledgements

This project was inspired by https://github.com/eshmu/gphotos-upload
