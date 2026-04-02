"""
Octopus AI — Image Tentacle 🎨
Generate images using OpenAI DALL-E.
"""
import os
import base64
import uuid
import logging
from pathlib import Path
from tools import BaseTool

logger = logging.getLogger("octopus.image_tool")


class ImageTool(BaseTool):
    name = "image_generate"
    description = "Generate images using AI. Creates images from text descriptions using DALL-E. Returns the image as a base64 string and saves it to disk."
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the image to generate",
            },
            "size": {
                "type": "string",
                "description": "Image size: '1024x1024', '1024x1792', or '1792x1024' (default: 1024x1024)",
            },
            "quality": {
                "type": "string",
                "description": "Image quality: 'standard' or 'hd' (default: standard)",
            },
        },
        "required": ["prompt"],
    }

    async def execute(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs,
    ) -> dict:
        try:
            from openai import AsyncOpenAI
            from config import get_config

            config = get_config()
            api_key = config.get("api_keys", {}).get("openai", "")

            if not api_key:
                return {
                    "status": "error",
                    "error": "OpenAI API key required for image generation. Set it in Settings.",
                }

            # Validate parameters
            valid_sizes = ["1024x1024", "1024x1792", "1792x1024"]
            if size not in valid_sizes:
                size = "1024x1024"

            if quality not in ("standard", "hd"):
                quality = "standard"

            client = AsyncOpenAI(api_key=api_key)

            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                response_format="b64_json",
                n=1,
            )

            image_data = response.data[0].b64_json
            revised_prompt = response.data[0].revised_prompt or prompt

            # Save to disk
            output_dir = Path(__file__).parent.parent.parent / "data" / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"img_{uuid.uuid4().hex[:8]}.png"
            filepath = output_dir / filename

            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_data))

            return {
                "status": "success",
                "message": f"Image generated and saved to {filepath}",
                "path": str(filepath),
                "revised_prompt": revised_prompt,
                "size": size,
                "quality": quality,
                "image_base64": image_data[:100] + "...(truncated)",
            }

        except ImportError:
            return {
                "status": "error",
                "error": "openai package not installed. Run: pip install openai",
            }
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"status": "error", "error": str(e)}
