from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pprint import pprint
import sys
import os
import gogrepoc

app = FastAPI(title="GOG Repo API")


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateRequest(BaseModel):
    os_list: List[str] = []
    lang_list: List[str] = []
    skipknown: bool = False
    updateonly: bool = False
    full: bool = True
    ids: List[str] = []
    skipids: List[str] = []
    skiphidden: bool = False
    installers: str = "standalone"
    resumemode: str = "noresume"
    strictverify: bool = False
    strictdupe: bool = False
    lenientdownloadsupdate: bool = True
    strictextrasupdate: bool = False
    md5xmls: bool = False
    nochangelogs: bool = True


class DownloadRequest(BaseModel):
    savedir: str
    skipextras: bool = False
    skipids: List[str] = []
    dryrun: bool = False
    ids: List[str] = []
    os_list: List[str] = []
    lang_list: List[str] = []
    skipgalaxy: bool = False
    skipstandalone: bool = False
    skipshared: bool = False
    skipfiles: List[str] = []
    covers: bool = False
    backgrounds: bool = False
    skippreallocation: bool = False
    clean_old_images: bool = True
    downloadlimit: Optional[float] = None
    compress_downloads: bool = False


@app.post("/login")
async def login(request: LoginRequest):
    try:
        gogrepoc.cmd_login(request.username, request.password)
        return {"status": "success", "message": "Login successful"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/update")
async def update(request: UpdateRequest):
    try:
        gogrepoc.cmd_update(
            request.os_list,
            request.lang_list,
            request.skipknown,
            request.updateonly,
            not request.full,
            request.ids,
            request.skipids,
            request.skiphidden,
            request.installers,
            request.resumemode,
            request.strictverify,
            request.strictdupe,
            request.lenientdownloadsupdate,
            request.strictextrasupdate,
            request.md5xmls,
            request.nochangelogs,
        )
        return {"status": "success", "message": "Update completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download")
async def download(request: DownloadRequest):
    try:
        gogrepoc.cmd_download(
            request.savedir,
            request.skipextras,
            request.skipids,
            request.dryrun,
            request.ids,
            request.os_list,
            request.lang_list,
            request.skipgalaxy,
            request.skipstandalone,
            request.skipshared,
            request.skipfiles,
            request.covers,
            request.backgrounds,
            request.skippreallocation,
            request.clean_old_images,
            request.downloadlimit,
        )

        if request.compress_downloads:
            # TODO: rename function
            gogrepoc.compress_folders(request.savedir)
            return {
                "status": "success",
                "message": "Download and compression completed successfully",
            }

        return {"status": "success", "message": "Download completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/manifest")
async def get_manifest():
    try:
        manifest = gogrepoc.load_manifest()
        downloaded_manifest = gogrepoc.load_downloaded_games()

        # Compare both manifests to find downloaded games
        # if a game exists in the downloaded manifest, remove it from the main manifest
        for game in downloaded_manifest:
            # game md5
            # game.gog_data.md5_xml.md5
            game_md5 = game.md5
            if game_md5:
                # check m.downloads[0].md5 first,
                # if it doesn't, try extras[0].md5
                for m in manifest:
                    if m.downloads and m.downloads[0].md5 == game_md5:
                        manifest.remove(m)
                        break
                    elif m.extras and m.extras[0].md5 == game_md5:
                        manifest.remove(m)
                        break

        # Convert the manifest items to a simpler format for the frontend
        # Format the title by replacing underscores with spaces and capitalizing each word
        games = [
            {
                "id": game.id,
                "title": " ".join(
                    word.capitalize() for word in game.title.replace("_", " ").split()
                ),
            }
            for game in manifest
        ]
        downloaded_games = [
            {
                "id": game.md5,
                "title": " ".join(
                    word.capitalize() for word in game.desc.replace("_", " ").split()
                ),
                "selectable": "False",
            }
            for game in downloaded_manifest
        ]

        return {
            "status": "success",
            "available_games": games,
            "downloaded_games": downloaded_games,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-auth")
async def check_auth():
    try:
        gogrepoc.makeGOGSession()
        # If we get here, the token is valid
        return {"status": "success", "isAuthenticated": True}
    except Exception as e:
        return {"status": "error", "isAuthenticated": False, "detail": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
