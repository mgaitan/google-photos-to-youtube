[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb)


## Setup

1. Copy client_id.json.dist as client_id.json

And follow https://developers.google.com/photos/library/guides/get-started

You require permissions on google Photos and Youtube data v3 APIs. 


2. Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` in the client_id.json file with the provided Client ID. 

3. Locally "python google_photos_to_youtube.py" to generate the file `token.json`

4. Open the notebook in colab uploading `client_id.json` and `token.json` if needed. Alternatively you can run it locally in Jupyter Lab. 


## Acknowledgements

This project is based on the following projects:

* https://github.com/eshmu/gphotos-upload
