from PIL import Image
import collections

def get_dominant_color(image_path):
    img = Image.open(image_path)
    img = img.convert("RGB")
    colors = img.getcolors(maxcolors=1000000)
    
    # Sort by count (descending)
    colors.sort(key=lambda x: x[0], reverse=True)
    
    print("Top 5 colors:")
    for count, color in colors[:5]:
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
        print(f"{hex_color}: {count}")
        
    # Heuristic: Ignore white/black/gray background if needed, but let's see the raw top 1 first.
    most_frequent = colors[0]
    hex_color = '#{:02x}{:02x}{:02x}'.format(*most_frequent[1])
    return hex_color

if __name__ == "__main__":
    path = r"E:\0 Projects\LLM Analysis Quiz\workspace\downloads\heatmap.png"
    try:
        dom = get_dominant_color(path)
        print(f"Dominant Color: {dom}")
        expected = "#b45a1e"
        if dom.lower() == expected.lower():
            print("SUCCESS: Matches expected color.")
        else:
            print(f"FAILURE: Does not match expected {expected}.")
    except Exception as e:
        print(f"Error: {e}")
