from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pprint import pprint
import sys
import os


# Add parent directory to path so we can import gogrepoc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gogrepoc

app = FastAPI(title="GOG Repo API")

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Request/Response Models
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
            request.nochangelogs
        )
        return {"status": "success", "message": "Update completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download")
async def download(request: DownloadRequest):
    try:
        if request.downloadlimit is not None:
            request.downloadlimit = request.downloadlimit * 1024.0 * 1024.0  # Convert to Bytes
        
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
            request.downloadlimit
        )
        return {"status": "success", "message": "Download completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/manifest")
async def get_manifest():
    try:
        maifest_path = os.path.join(project_root, gogrepoc.MANIFEST_FILENAME)
        manifest = gogrepoc.load_manifest(filepath=maifest_path)
        # Convert the manifest items to a simpler format for the frontend
        games = [{"id": game.id, "title": game.title, "folder_name": game.folder_name} for game in manifest]
        return {"status": "success", "games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-auth")
async def check_auth():
    try:
        token_path = os.path.join(project_root, gogrepoc.TOKEN_FILENAME)
        session = gogrepoc.makeGOGSession(tokenPath=token_path)
        # If we get here, the token is valid
        return {"status": "success", "isAuthenticated": True}
    except Exception as e:
        return {"status": "error", "isAuthenticated": False, "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
