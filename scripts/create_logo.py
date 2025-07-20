from PIL import Image, ImageDraw, ImageFont
import os

def create_folder_organizer_logo(output_path="logo.png", size=(200, 200), bg_color=(240, 240, 240), 
                                folder_color=(255, 193, 7), accent_color=(33, 150, 243)):
    """
    Create a simple folder organizer logo
    
    Args:
        output_path: Path to save the logo
        size: Size of the logo (width, height)
        bg_color: Background color in RGB
        folder_color: Main folder color in RGB
        accent_color: Accent color for organization elements in RGB
    """
    # Create a new image with a white background
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    width, height = size
    margin = width // 10
    
    # Draw main folder
    folder_width = width - 2 * margin
    folder_height = height - 2 * margin
    tab_height = folder_height // 5
    
    # Folder tab
    draw.rectangle(
        [(margin + folder_width // 5, margin), 
         (margin + folder_width // 5 * 3, margin + tab_height)],
        fill=folder_color,
        outline=(0, 0, 0),
        width=2
    )
    
    # Folder body
    draw.rectangle(
        [(margin, margin + tab_height), 
         (margin + folder_width, margin + folder_height)],
        fill=folder_color,
        outline=(0, 0, 0),
        width=2
    )
    
    # Draw organization lines (representing files)
    line_spacing = (folder_height - tab_height) // 5
    line_width = folder_width - margin
    line_start_x = margin + margin // 2
    
    for i in range(4):
        y_pos = margin + tab_height + line_spacing * (i + 1)
        draw.rectangle(
            [(line_start_x, y_pos), 
             (line_start_x + line_width, y_pos + line_spacing // 3)],
            fill=accent_color,
            outline=(0, 0, 0),
            width=1
        )
    
    # Add a small sorting arrow
    arrow_size = width // 8
    arrow_x = margin + folder_width - arrow_size - margin
    arrow_y = margin + tab_height + folder_height // 4
    
    # Arrow body
    draw.rectangle(
        [(arrow_x, arrow_y), 
         (arrow_x + arrow_size // 2, arrow_y + arrow_size * 1.5)],
        fill=(50, 50, 50)
    )
    
    # Arrow head
    draw.polygon(
        [(arrow_x - arrow_size // 2, arrow_y + arrow_size),
         (arrow_x + arrow_size, arrow_y + arrow_size),
         (arrow_x + arrow_size // 4, arrow_y + arrow_size * 2)],
        fill=(50, 50, 50)
    )
    
    # Save the image
    img.save(output_path)
    print(f"Logo saved to {os.path.abspath(output_path)}")
    
    # Create icon version (ICO format for Windows)
    icon_path = output_path.replace('.png', '.ico')
    img.save(icon_path, format='ICO', sizes=[(32, 32), (64, 64), (128, 128)])
    print(f"Icon saved to {os.path.abspath(icon_path)}")
    
    return os.path.abspath(output_path), os.path.abspath(icon_path)

if __name__ == "__main__":
    # Create the logo with default settings
    png_path, ico_path = create_folder_organizer_logo()
    
    # Optionally create variations
    # Blue theme
    create_folder_organizer_logo("logo_blue.png", 
                               folder_color=(66, 133, 244), 
                               accent_color=(255, 193, 7))
    
    # Green theme
    create_folder_organizer_logo("logo_green.png", 
                               folder_color=(76, 175, 80), 
                               accent_color=(255, 152, 0))
