import io
import base64
import matplotlib.pyplot as plt
from app.tools.csv_loader import sandbox

async def plot_to_base64(args):
    """
    Executes plotting code and returns base64 image.
    args:
      - code: str
    """
    code = args.get("code")
    if not code:
        return {"error": "No code provided"}
    
    try:
        plt.clf()
        res = sandbox.execute(code)
        if res.get("error"):
            return res
            
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode("utf-8")
        plt.clf()
        
        return {
            "stdout": res.get("stdout"),
            "image_base64": img_str
        }
    except Exception as e:
        return {"error": str(e)}
