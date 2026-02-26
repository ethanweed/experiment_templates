"""
mouse_viz.py

This module contains functions to assist in organizing and plotting data from our mouse-tracking reading experiments.



"""

from PIL import ImageFont

def get_participant_id(raw):
    return raw.split('/')[-1].split('_')[0]

def get_reading_trials(df):
    df_reading = df[df['trial_type'] == 'reading']
    return df_reading

def get_mouse_data(df_reading,trial_num=0):
    mouse_data = df_reading[df_reading['mouse_tracking_data'].apply(len) > 0]
    return mouse_data["mouse_tracking_data"].iloc[trial_num]

def get_canvas_dimensions(df_reading, trial_num=0):
    trial = df_reading.iloc[trial_num]
    return trial['canvas_width'], trial['canvas_height']

def load_font(size=18):
    """Load a TrueType font, falling back to default if necessary."""
    font_paths = [
        'arial.ttf',
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial.ttf',
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    print("Warning: Using default font. Text positioning may be less accurate.")
    return ImageFont.load_default()


def get_word_positions(text, canvas_width, font):
    """Calculate pixel positions for each word in the text."""
    text_start_x = HORIZONTAL_PADDING // 2
    text_start_y = VERTICAL_PADDING_TOP + 10
    available_width = canvas_width - HORIZONTAL_PADDING
    words = text.split(' ')
    word_positions = []
    current_line_text = ''
    current_x = text_start_x
    line_index = 0

    for word in words:
        test_line = current_line_text + (' ' if current_line_text else '') + word
        bbox = font.getbbox(test_line)
        test_width = bbox[2] - bbox[0]

        if test_width > available_width and current_line_text:
            line_index += 1
            current_line_text = word
            current_x = text_start_x
        else:
            if current_line_text:
                prev_bbox = font.getbbox(current_line_text + ' ')
                current_x = text_start_x + (prev_bbox[2] - prev_bbox[0])
            current_line_text = test_line

        word_bbox = font.getbbox(word)
        word_width = word_bbox[2] - word_bbox[0]
        y_position = text_start_y + (line_index * LINE_HEIGHT)

        word_positions.append({
            'word': word, 
            'word_index': len(word_positions),
            'x_start': current_x, 
            'x_end': current_x + word_width,
            'y_position': y_position, 
            'line_index': line_index
        })
        current_x += word_width

    return word_positions

def get_text_content(df_reading, trial_num=0):
    return df_reading.iloc[trial_num]['text_content']

def compute_word_durations(df_reading, canvas_width=canvas_width, text=text, word_positions=word_positions, x_tolerance=5, y_tolerance=15):
    """
    Compute duration spent on each word from mouse tracking data.
    Returns a DataFrame with word positions and durations.
    """
    
    tracking = mouse_data
    canvas_width = canvas_width
    text = text
    word_positions = word_positions
    word_durations = {i: 0.0 for i in range(len(word_positions))}

    n = len(tracking)
    if n < 2:
        return pd.DataFrame([{
            'word_number': wp['word_index'],
            'word': wp['word'],
            'duration_ms': 0.0,
            'x_start': wp['x_start'],
            'x_end': wp['x_end'],
            'y_position': wp['y_position'],
            'line_number': wp['line_index']
        } for wp in word_positions])

    for i in range(n - 1):
        point = tracking[i]
        next_point = tracking[i + 1]

        x, y = point['x'], point['y']
        dt = next_point['timestamp'] - point['timestamp']

        if dt <= 0 or dt > 1000:
            continue

        for wp in word_positions:
            if (wp['x_start'] - x_tolerance) <= x <= (wp['x_end'] + x_tolerance):
                if (wp['y_position'] - y_tolerance) <= y <= (wp['y_position'] + y_tolerance):
                    word_durations[wp['word_index']] += dt
                    break

    data = []
    for wp in word_positions:
        data.append({
            'word_number': wp['word_index'],
            'word': wp['word'],
            'duration_ms': round(word_durations[wp['word_index']], 2),
            'x_start': round(wp['x_start'], 1),
            'x_end': round(wp['x_end'], 1),
            'y_position': round(wp['y_position'], 1),
            'line_number': wp['line_index']
        })

    return pd.DataFrame(data)