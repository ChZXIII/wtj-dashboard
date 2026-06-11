import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

def process_logo(logo_path):
    # Load the logo and convert to RGBA. The original has a transparent background
    logo = Image.open(logo_path).convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    return logo

def generate_thumbnail(base_image_path, logo_img, output_path, layout_type="top"):
    # Load base image (1024x1024)
    base = Image.open(base_image_path).convert("RGBA")
    w, h = base.size # 1024, 1024
    
    # Target size for 16:9 aspect ratio (1820x1024)
    target_w = int(h * 16 / 9) # 1820
    if layout_type == "right_aligned_huge":
        pad_w = target_w - w # 796
    else:
        pad_w = (target_w - w) // 2 # 398
    
    # 1. Create a blurred background from the base image to prevent barcode stretching streaks
    # Scale base to cover the 16:9 canvas
    bg_scaled = base.resize((target_w, target_w), Image.Resampling.LANCZOS)
    bg_cropped = bg_scaled.crop((0, (target_w - h) // 2, target_w, (target_w + h) // 2))
    
    # Apply heavy blur
    blurred_bg = bg_cropped.filter(ImageFilter.GaussianBlur(60))
    
    # Darken the blurred background with a dark solid color
    dark_overlay = Image.new("RGBA", (target_w, h), (18, 16, 32, 180)) # 70% opacity dark purple
    canvas = Image.alpha_composite(blurred_bg, dark_overlay)
    
    # 2. Blend the central square image with soft edges using a gradient mask
    mask = Image.new("L", (w, h), 255)
    mask_draw = ImageDraw.Draw(mask)
    
    blend_width = 120
    # Left gradient
    for x in range(blend_width):
        alpha = int(255 * (x / blend_width))
        mask_draw.line([(x, 0), (x, h)], fill=alpha)
        
    # Right gradient
    for x in range(blend_width):
        alpha = int(255 * (x / blend_width))
        mask_draw.line([(w - 1 - x, 0), (w - 1 - x, h)], fill=alpha)
        
    # Paste base image onto the canvas using the gradient mask
    canvas.paste(base, (pad_w, 0), mask=mask)
    
    # 3. Create separate overlay image for transparent drawings and text to preserve canvas opacity
    overlay = Image.new("RGBA", (target_w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Apply a subtle vignette to the entire canvas to frame the composition
    for x in range(pad_w):
        alpha = int(255 * (1 - (x / pad_w) ** 2) * 0.4)
        overlay_draw.line([(x, 0), (x, h)], fill=(18, 16, 32, alpha))
    for x in range(pad_w + w, target_w):
        dist = x - (pad_w + w)
        alpha = int(255 * (dist / pad_w) ** 2 * 0.4)
        overlay_draw.line([(x, 0), (x, h)], fill=(18, 16, 32, alpha))
        
    # Load fonts
    font_path_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    font_path_thai = "/System/Library/Fonts/Supplemental/SukhumvitSet.ttc"
    
    # Positions and sizes based on layout type
    if layout_type == "top":
        logo_h = 100
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 80
        logo_y = 80
        
        text_x = logo_x + logo_w + 25
        text_y = logo_y + 3
        
        font_title = ImageFont.truetype(font_path_bold, 64)
        font_subtitle = ImageFont.truetype(font_path_thai, 34, index=2) # Bold
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Title Shadow and Text
        overlay_draw.text((text_x + 3, text_y + 3), "GAME BALANCER", fill=(0, 0, 0, 220), font=font_title)
        overlay_draw.text((text_x, text_y), "GAME BALANCER", fill=(255, 255, 255, 255), font=font_title)
        
        # Subtitle Shadow and Text (Thai)
        sub_y = text_y + 72
        overlay_draw.text((text_x + 2, sub_y + 2), "นักปรับสมดุลเกม", fill=(0, 0, 0, 200), font=font_subtitle)
        overlay_draw.text((text_x, sub_y), "นักปรับสมดุลเกม", fill=(210, 210, 230, 255), font=font_subtitle)
        
    elif layout_type == "middle":
        logo_h = 130
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 100
        logo_y = 442
        
        text_x = logo_x + logo_w + 30
        text_y = logo_y + 8
        
        font_title = ImageFont.truetype(font_path_bold, 76)
        font_subtitle = ImageFont.truetype(font_path_thai, 38, index=2)
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Title Shadow and Text
        overlay_draw.text((text_x + 4, text_y + 4), "GAME BALANCER", fill=(0, 0, 0, 220), font=font_title)
        overlay_draw.text((text_x, text_y), "GAME BALANCER", fill=(255, 255, 255, 255), font=font_title)
        
        # Subtitle Shadow and Text (Thai)
        sub_y = text_y + 86
        overlay_draw.text((text_x + 2, sub_y + 2), "นักปรับสมดุลเกม", fill=(0, 0, 0, 200), font=font_subtitle)
        overlay_draw.text((text_x, sub_y), "นักปรับสมดุลเกม", fill=(210, 210, 230, 255), font=font_subtitle)
        
    elif layout_type == "premium_top":
        logo_h = 110
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 80
        logo_y = 70
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Draw "STORY" badge next to logo
        font_story = ImageFont.truetype(font_path_bold, 22)
        story_text = "STORY"
        story_bbox = overlay_draw.textbbox((0, 0), story_text, font=font_story)
        story_w = story_bbox[2] - story_bbox[0]
        story_h = story_bbox[3] - story_bbox[1]
        
        badge_padding_x = 16
        badge_padding_y = 8
        badge_w = story_w + 2 * badge_padding_x
        badge_h = story_h + 2 * badge_padding_y
        
        badge_x = logo_x + logo_w + 20
        badge_y = logo_y + (logo_h - badge_h) // 2
        
        overlay_draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=badge_h // 2,
            fill=(220, 53, 69, 220), # Crimson Red
            outline=(255, 255, 255, 255),
            width=2
        )
        overlay_draw.text((badge_x + badge_padding_x, badge_y + badge_padding_y - 2), story_text, fill=(255, 255, 255, 255), font=font_story)
        
        # Main Title (size 76)
        title_x = 80
        title_y = logo_y + logo_h + 30
        font_title = ImageFont.truetype(font_path_bold, 76)
        
        overlay_draw.text((title_x + 5, title_y + 5), "GAME BALANCER", fill=(0, 0, 0, 220), font=font_title)
        overlay_draw.text((title_x, title_y), "GAME BALANCER", fill=(255, 255, 255, 255), font=font_title)
        
        # Subtitle: นักปรับสมดุลเกม (size 44)
        sub_x = 80
        sub_y = title_y + 100
        font_subtitle = ImageFont.truetype(font_path_thai, 44, index=2)
        
        overlay_draw.text((sub_x + 3, sub_y + 3), "นักปรับสมดุลเกม", fill=(0, 0, 0, 200), font=font_subtitle)
        overlay_draw.text((sub_x, sub_y), "นักปรับสมดุลเกม", fill=(210, 210, 230, 255), font=font_subtitle)
        
        # Tagline: ผู้บงการชะตาฮีโร่ (size 38)
        tag_x = 80
        tag_y = sub_y + 60
        font_tagline = ImageFont.truetype(font_path_thai, 38, index=2)
        tag_text = "ผู้บงการชะตาฮีโร่"
        
        overlay_draw.text((tag_x + 3, tag_y + 3), tag_text, fill=(0, 0, 0, 200), font=font_tagline)
        overlay_draw.text((tag_x, tag_y), tag_text, fill=(255, 204, 0, 255), font=font_tagline) # Gold color
        
    elif layout_type == "premium_stacked":
        logo_h = 110
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 80
        logo_y = 60
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Draw "STORY" badge next to logo
        font_story = ImageFont.truetype(font_path_bold, 22)
        story_text = "STORY"
        story_bbox = overlay_draw.textbbox((0, 0), story_text, font=font_story)
        story_w = story_bbox[2] - story_bbox[0]
        story_h = story_bbox[3] - story_bbox[1]
        
        badge_padding_x = 16
        badge_padding_y = 8
        badge_w = story_w + 2 * badge_padding_x
        badge_h = story_h + 2 * badge_padding_y
        
        badge_x = logo_x + logo_w + 20
        badge_y = logo_y + (logo_h - badge_h) // 2
        
        overlay_draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=badge_h // 2,
            fill=(220, 53, 69, 220), # Crimson Red
            outline=(255, 255, 255, 255),
            width=2
        )
        overlay_draw.text((badge_x + badge_padding_x, badge_y + badge_padding_y - 2), story_text, fill=(255, 255, 255, 255), font=font_story)
        
        # Stacked Title (size 110)
        # GAME
        title1_x = 80
        title1_y = logo_y + logo_h + 25
        font_title_big = ImageFont.truetype(font_path_bold, 110)
        
        overlay_draw.text((title1_x + 5, title1_y + 5), "GAME", fill=(0, 0, 0, 220), font=font_title_big)
        overlay_draw.text((title1_x, title1_y), "GAME", fill=(255, 255, 255, 255), font=font_title_big)
        
        # BALANCER
        title2_x = 80
        title2_y = title1_y + 115
        
        overlay_draw.text((title2_x + 5, title2_y + 5), "BALANCER", fill=(0, 0, 0, 220), font=font_title_big)
        overlay_draw.text((title2_x, title2_y), "BALANCER", fill=(255, 255, 255, 255), font=font_title_big)
        
        # Subtitle: นักปรับสมดุลเกม (size 44)
        sub_x = 80
        sub_y = title2_y + 130
        font_subtitle = ImageFont.truetype(font_path_thai, 44, index=2)
        
        overlay_draw.text((sub_x + 3, sub_y + 3), "นักปรับสมดุลเกม", fill=(0, 0, 0, 200), font=font_subtitle)
        overlay_draw.text((sub_x, sub_y), "นักปรับสมดุลเกม", fill=(210, 210, 230, 255), font=font_subtitle)
        
        # Tagline: ผู้บงการชะตาฮีโร่ (size 38)
        tag_x = 80
        tag_y = sub_y + 65
        font_tagline = ImageFont.truetype(font_path_thai, 38, index=2)
        tag_text = "ผู้บงการชะตาฮีโร่"
        
        overlay_draw.text((tag_x + 3, tag_y + 3), tag_text, fill=(0, 0, 0, 200), font=font_tagline)
        overlay_draw.text((tag_x, tag_y), tag_text, fill=(255, 204, 0, 255), font=font_tagline) # Gold color
        
    elif layout_type == "huge_thai":
        logo_h = 100
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 80
        logo_y = 60
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Draw "STORY" badge next to logo
        font_story = ImageFont.truetype(font_path_bold, 22)
        story_text = "STORY"
        story_bbox = overlay_draw.textbbox((0, 0), story_text, font=font_story)
        story_w = story_bbox[2] - story_bbox[0]
        story_h = story_bbox[3] - story_bbox[1]
        
        badge_padding_x = 16
        badge_padding_y = 8
        badge_w = story_w + 2 * badge_padding_x
        badge_h = story_h + 2 * badge_padding_y
        
        badge_x = logo_x + logo_w + 20
        badge_y = logo_y + (logo_h - badge_h) // 2
        
        overlay_draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=badge_h // 2,
            fill=(220, 53, 69, 220), # Crimson Red
            outline=(255, 255, 255, 255),
            width=2
        )
        overlay_draw.text((badge_x + badge_padding_x, badge_y + badge_padding_y - 2), story_text, fill=(255, 255, 255, 255), font=font_story)
        
        # Main Title (smaller English, size 56)
        title_x = 80
        title_y = logo_y + logo_h + 25
        font_title = ImageFont.truetype(font_path_bold, 56)
        
        overlay_draw.text((title_x + 4, title_y + 4), "GAME BALANCER", fill=(0, 0, 0, 220), font=font_title)
        overlay_draw.text((title_x, title_y), "GAME BALANCER", fill=(255, 255, 255, 255), font=font_title)
        
        # Subtitle: นักปรับสมดุลเกม (Massive Thai, size 80!)
        sub_x = 80
        sub_y = title_y + 80
        font_subtitle = ImageFont.truetype(font_path_thai, 80, index=2)
        
        overlay_draw.text((sub_x + 5, sub_y + 5), "นักปรับสมดุลเกม", fill=(0, 0, 0, 220), font=font_subtitle)
        overlay_draw.text((sub_x, sub_y), "นักปรับสมดุลเกม", fill=(255, 255, 255, 255), font=font_subtitle)
        
        # Tagline: ผู้บงการชะตาฮีโร่ (size 42, gold color)
        tag_x = 80
        tag_y = sub_y + 110
        font_tagline = ImageFont.truetype(font_path_thai, 42, index=2)
        tag_text = "ผู้บงการชะตาฮีโร่"
        
        overlay_draw.text((tag_x + 3, tag_y + 3), tag_text, fill=(0, 0, 0, 200), font=font_tagline)
        overlay_draw.text((tag_x, tag_y), tag_text, fill=(255, 204, 0, 255), font=font_tagline) # Gold color
        
    elif layout_type == "right_aligned_huge":
        logo_h = 100
        aspect_ratio = logo_img.width / logo_img.height
        logo_w = int(logo_h * aspect_ratio)
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 100
        logo_y = 120
        
        # Paste logo
        overlay.paste(logo_resized, (logo_x, logo_y), mask=logo_resized)
        
        # Draw "STORY" badge next to logo
        font_story = ImageFont.truetype(font_path_bold, 22)
        story_text = "STORY"
        story_bbox = overlay_draw.textbbox((0, 0), story_text, font=font_story)
        story_w = story_bbox[2] - story_bbox[0]
        story_h = story_bbox[3] - story_bbox[1]
        
        badge_padding_x = 16
        badge_padding_y = 8
        badge_w = story_w + 2 * badge_padding_x
        badge_h = story_h + 2 * badge_padding_y
        
        badge_x = logo_x + logo_w + 20
        badge_y = logo_y + (logo_h - badge_h) // 2
        
        overlay_draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=badge_h // 2,
            fill=(220, 53, 69, 220), # Crimson Red
            outline=(255, 255, 255, 255),
            width=2
        )
        overlay_draw.text((badge_x + badge_padding_x, badge_y + badge_padding_y - 2), story_text, fill=(255, 255, 255, 255), font=font_story)
        
        # Main Title (English) - Size 85
        title_x = 100
        title_y = logo_y + logo_h + 40
        font_title = ImageFont.truetype(font_path_bold, 85)
        
        overlay_draw.text((title_x + 6, title_y + 6), "GAME BALANCER", fill=(0, 0, 0, 220), font=font_title)
        overlay_draw.text((title_x, title_y), "GAME BALANCER", fill=(255, 255, 255, 255), font=font_title)
        
        # Subtitle: นักปรับสมดุลเกม (Massive Thai) - Size 135!
        sub_x = 100
        sub_y = title_y + 105
        font_subtitle = ImageFont.truetype(font_path_thai, 135, index=2)
        
        overlay_draw.text((sub_x + 8, sub_y + 8), "นักปรับสมดุลเกม", fill=(0, 0, 0, 220), font=font_subtitle)
        overlay_draw.text((sub_x, sub_y), "นักปรับสมดุลเกม", fill=(255, 255, 255, 255), font=font_subtitle)
        
        # Tagline: ผู้บงการชะตาฮีโร่ - Size 54 (gold color)
        tag_x = 100
        tag_y = sub_y + 165
        font_tagline = ImageFont.truetype(font_path_thai, 54, index=2)
        tag_text = "ผู้บงการชะตาฮีโร่"
        
        overlay_draw.text((tag_x + 4, tag_y + 4), tag_text, fill=(0, 0, 0, 200), font=font_tagline)
        overlay_draw.text((tag_x, tag_y), tag_text, fill=(255, 204, 0, 255), font=font_tagline) # Gold color
        
    # Alpha composite the overlay onto the main canvas
    final_canvas = Image.alpha_composite(canvas, overlay)
    
    # Resize final image to standard 1280x720 YouTube Thumbnail size
    final_thumbnail = final_canvas.resize((1280, 720), Image.Resampling.LANCZOS)
    final_thumbnail.save(output_path, "PNG")
    print(f"Generated {layout_type} layout thumbnail at: {output_path}")

if __name__ == "__main__":
    logo_path = "/Users/chz/.gemini/antigravity/brain/34d37b1f-f8a6-4336-9a4d-a8edb3079e36/media__1779351900558.png"
    
    out_dir = "/Users/chz/Desktop/1st_Agent/Team Agent Content/workspace/game_balancer/images"
    brain_dir = "/Users/chz/.gemini/antigravity/brain/34d37b1f-f8a6-4336-9a4d-a8edb3079e36"
    os.makedirs(out_dir, exist_ok=True)
    
    logo_img = process_logo(logo_path)
    
    # 1. Style 1: Claymation Scale Style
    base_style1 = os.path.join(brain_dir, "clean_balancer_base_1779340809178.png")
    generate_thumbnail(base_style1, logo_img, os.path.join(out_dir, "style1_clay_huge.png"), layout_type="huge_thai")
    generate_thumbnail(base_style1, logo_img, os.path.join(brain_dir, "style1_clay_huge.png"), layout_type="huge_thai")
    
    # 2. Style 2: Extremely Realistic Workspace Style (Updated to right-aligned layout and larger text)
    base_style2 = os.path.join(brain_dir, "realistic_balancer_base_1779355063417.png")
    generate_thumbnail(base_style2, logo_img, os.path.join(out_dir, "style2_realistic_huge.png"), layout_type="right_aligned_huge")
    generate_thumbnail(base_style2, logo_img, os.path.join(brain_dir, "style2_realistic_huge.png"), layout_type="right_aligned_huge")
    
    # 3. Style 3: Nam's Creative Out-of-the-Box Style
    base_style3 = os.path.join(brain_dir, "nam_creative_concept_base_1779355089870.png")
    generate_thumbnail(base_style3, logo_img, os.path.join(out_dir, "style3_nam_huge.png"), layout_type="huge_thai")
    generate_thumbnail(base_style3, logo_img, os.path.join(brain_dir, "style3_nam_huge.png"), layout_type="huge_thai")
    
    # Also save Style 2 as the chosen default clean_thumbnail_16_9.png (right-aligned layout)
    generate_thumbnail(base_style2, logo_img, os.path.join(out_dir, "clean_thumbnail_16_9.png"), layout_type="right_aligned_huge")
    generate_thumbnail(base_style2, logo_img, os.path.join(brain_dir, "clean_thumbnail_16_9.png"), layout_type="right_aligned_huge")
