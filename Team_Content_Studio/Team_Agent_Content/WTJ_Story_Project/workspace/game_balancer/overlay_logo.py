import os
from PIL import Image, ImageOps

def process_logo(logo_path):
    logo = Image.open(logo_path).convert("RGBA")
    datas = logo.getdata()
    
    new_data = []
    for item in datas:
        # Check if the pixel is white or very close to white
        if item[0] > 245 and item[1] > 245 and item[2] > 245:
            # Make it transparent
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    logo.putdata(new_data)
    
    # Crop the logo to the bounding box of non-transparent pixels
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
        
    return logo

def overlay_logo(thumbnail_path, logo_img, output_path, position="top_left"):
    thumb = Image.open(thumbnail_path).convert("RGBA")
    
    # Calculate size for the logo (e.g. 10% of the thumbnail height)
    thumb_w, thumb_h = thumb.size
    logo_h = int(thumb_h * 0.12)
    aspect_ratio = logo_img.width / logo_img.height
    logo_w = int(logo_h * aspect_ratio)
    
    logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    
    # Add a small padding
    padding = int(thumb_h * 0.04)
    
    if position == "top_left":
        pos = (padding, padding)
    elif position == "top_right":
        pos = (thumb_w - logo_w - padding, padding)
    elif position == "bottom_left":
        pos = (padding, thumb_h - logo_h - padding)
    else: # bottom_right
        pos = (thumb_w - logo_w - padding, thumb_h - logo_h - padding)
        
    # Paste logo onto thumbnail
    combined = Image.new("RGBA", thumb.size)
    combined.paste(thumb, (0, 0))
    combined.paste(logo_resized, pos, mask=logo_resized)
    
    combined.convert("RGB").save(output_path, "PNG")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    logo_path = "/Users/chz/.gemini/antigravity/brain/34d37b1f-f8a6-4336-9a4d-a8edb3079e36/media__1779336049189.png"
    workspace_dir = "/Users/chz/Desktop/1st_Agent/Team Agent Content/workspace/game_balancer/images"
    
    logo_img = process_logo(logo_path)
    
    # Process Option A
    thumb_a = os.path.join(workspace_dir, "thumbnail_option_a.png")
    out_a = os.path.join(workspace_dir, "thumbnail_option_a_with_logo.png")
    overlay_logo(thumb_a, logo_img, out_a, position="top_left")
    
    # Process Option B
    thumb_b = os.path.join(workspace_dir, "thumbnail_option_b.png")
    out_b = os.path.join(workspace_dir, "thumbnail_option_b_with_logo.png")
    overlay_logo(thumb_b, logo_img, out_b, position="top_left")
