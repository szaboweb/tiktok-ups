import os
import logging
from pathlib import Path

logger = logging.getLogger("TikTokEngine")

def upload_to_tiktok(video_path: str, description: str, hashtags: list = None) -> tuple[bool, str]:
    """
    Executes TikTok upload using tiktok-uploader and local cookies file.
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)
    cookies_path = os.getenv("TIKTOK_COOKIES_PATH", "auth/tiktok_cookies.txt")
    
    logger.info(f"[TIKTOK] Initializing TikTok upload workflow for: {os.path.basename(video_path)}")
    
    # Verify video file existence
    if not os.path.exists(video_path):
        err = f"[TIKTOK] Error: Video file not found at {video_path}"
        logger.error(err)
        return False, err
        
    # Verify cookies token file
    if not os.path.exists(cookies_path) or os.path.getsize(cookies_path) == 0:
        err = (
            f"[TIKTOK] Authentication token missing: '{cookies_path}' not found or empty. "
            f"Please export Netscape cookies from your authenticated browser session into '{cookies_path}'."
        )
        logger.error(err)
        return False, err

    full_caption = description
    if hashtags:
        full_caption += " " + " ".join(hashtags)
    
    logger.info(f"[TIKTOK] Prepared caption: {full_caption}")
    logger.info(f"[TIKTOK] Using cookie authentication from: {cookies_path}")
    
    try:
        from tiktok_uploader import upload_video
        
        logger.info("[TIKTOK] Spawning headless Playwright browser instance...")
        # tiktok-uploader upload_video call
        # Note: headless=True is default or standard in tiktok-uploader
        result = upload_video(
            filename=video_path,
            description=full_caption,
            cookies=cookies_path
        )
        
        if result:
            msg = f"[TIKTOK] Successfully uploaded {os.path.basename(video_path)} to TikTok."
            logger.info(msg)
            return True, msg
        else:
            msg = f"[TIKTOK] Upload failed or returned False for {os.path.basename(video_path)}."
            logger.error(msg)
            return False, msg
            
    except Exception as e:
        err = f"[TIKTOK] Execution exception during upload: {str(e)}"
        logger.error(err)
        return False, err
