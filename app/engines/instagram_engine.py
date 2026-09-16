import os
import logging
from pathlib import Path

logger = logging.getLogger("InstagramEngine")

def upload_to_instagram(video_path: str, description: str, hashtags: list = None) -> tuple[bool, str]:
    """
    Executes Instagram Reel/video upload using instagrapi and local session settings.
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    try:
        import imageio_ffmpeg
        os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
        
    session_path = os.getenv("INSTAGRAM_SESSION_PATH", "auth/instagram_session.json")
    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    
    logger.info(f"[INSTAGRAM] Initializing Instagram upload workflow for: {os.path.basename(video_path)}")
    
    if not os.path.exists(video_path):
        err = f"[INSTAGRAM] Error: Video file not found at {video_path}"
        logger.error(err)
        return False, err

    has_session = os.path.exists(session_path) and os.path.getsize(session_path) > 10
    has_creds = bool(username and password)
    
    if not has_session and not has_creds:
        err = (
            f"[INSTAGRAM] Authentication credentials missing: Neither valid session file "
            f"('{session_path}') nor INSTAGRAM_USERNAME/PASSWORD are configured in environment."
        )
        logger.error(err)
        return False, err

    full_caption = description
    if hashtags:
        full_caption += "\n\n" + " ".join(hashtags)

    logger.info(f"[INSTAGRAM] Caption prepared ({len(full_caption)} chars).")
    
    try:
        from instagrapi import Client
        cl = Client()
        
        if has_session:
            logger.info(f"[INSTAGRAM] Loading local session cache from: {session_path}")
            cl.load_settings(session_path)
            # Re-login with session data
            if has_creds:
                cl.login(username, password)
        else:
            logger.info(f"[INSTAGRAM] Performing fresh login for user: {username}")
            cl.login(username, password)
            # Save settings for future sessions
            os.makedirs(os.path.dirname(session_path), exist_ok=True)
            cl.dump_settings(session_path)
            logger.info(f"[INSTAGRAM] Session saved to {session_path}")

        logger.info(f"[INSTAGRAM] Uploading short-form clip/reel to Instagram: {os.path.basename(video_path)}")
        media = cl.clip_upload(
            path=video_path,
            caption=full_caption
        )
        
        if media and hasattr(media, "pk"):
            msg = f"[INSTAGRAM] Successfully published Reel. Media ID: {media.pk}"
            logger.info(msg)
            return True, msg
        else:
            msg = f"[INSTAGRAM] Upload finished with response: {media}"
            logger.info(msg)
            return True, msg
            
    except Exception as e:
        err = f"[INSTAGRAM] Upload execution exception: {str(e)}"
        logger.error(err)
        return False, err
