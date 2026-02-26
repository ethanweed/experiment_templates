"""
mouse_viz.py

This module contains functions to assist in organizing and plotting data from our mouse-tracking reading experiments.



"""
# --- Constants ---
FONT_SIZE            = 18
LINE_HEIGHT          = 25
HORIZONTAL_PADDING   = 30
VERTICAL_PADDING_TOP = 20

import pathlib
import jsonlines
import pandas as pd
from mpl_toolkits.axes_grid1 import make_axes_locatable
from PIL import ImageFont
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap



def get_participant_id(raw):
    return pathlib.Path(raw).name.split('_')[0]

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


def get_word_positions(text, canvas_width, font,
                       horizontal_padding=HORIZONTAL_PADDING,
                       vertical_padding_top=VERTICAL_PADDING_TOP,
                       line_height=LINE_HEIGHT):

    """Calculate pixel positions for each word in the text."""
    text_start_x = horizontal_padding // 2
    text_start_y = vertical_padding_top + 10
    available_width = canvas_width - horizontal_padding
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

def compute_word_durations(df_reading, canvas_width=None, text=None, word_positions=None, x_tolerance=5, y_tolerance=15):
    """
    Compute duration spent on each word from mouse tracking data.
    Returns a DataFrame with word positions and durations.
    """
    
    if canvas_width is None:
        raise ValueError("canvas_width must be provided.")
    if text is None:
        raise ValueError("text must be provided.")
    if word_positions is None:
        raise ValueError("word_positions must be provided.")

    tracking = get_mouse_data(df_reading)
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


def build_data(raw_files, font=None):
    """
    Builds the data list from a list of raw JATOS .txt file paths.

    Args:
        raw_files : list of str
            List of file paths to raw JATOS .txt data files.

    font : PIL ImageFont
        Font object used for computing word positions.

    Returns
    -------
    list of dict
        One dictionary per trial, across all participants and files.
    """

    if font is None:
        font = load_font()  # uses load_font() function from this module

    data = []

    for raw in raw_files:
        with jsonlines.open(raw) as reader:
            lines = [line for line in reader]

        # Format 1: single line containing a list of trial dicts (e.g. 6138_2.txt)
        if len(lines) == 1 and isinstance(lines[0], list):
            df = pd.DataFrame(lines[0])

        # Format 2: one trial dict per line (e.g. 6138_3.txt)
        else:
            df = pd.DataFrame(lines)


        participant_id = get_participant_id(raw)
        reading_trials = get_reading_trials(df)

        for trial in range(len(reading_trials)):
            canvas_width, canvas_height = get_canvas_dimensions(reading_trials, trial_num=trial)
            text_content               = get_text_content(reading_trials, trial_num=trial)
            mouse_data                 = get_mouse_data(reading_trials, trial_num=trial)
            word_positions             = get_word_positions(text_content, canvas_width, font)
            word_durations             = compute_word_durations(reading_trials, canvas_width, text_content, word_positions)

            data.append({
                'participant_id': participant_id,
                'trial_num':      trial,
                'text_content':   text_content,
                'mouse_data':     mouse_data,
                'canvas_width':   canvas_width,
                'canvas_height':  canvas_height,
                'word_positions': word_positions,
                'word_durations': word_durations,
            })

    return data


def plot_text_heatmap(participant, title=None, figsize=(14, 6)):
    """
    Visual heatmap showing the text with words colored by duration.
    Reads directly from a participant dictionary in the `data` list.
    """
    df           = participant['word_durations']
    canvas_width  = participant['canvas_width']
    canvas_height = participant['canvas_height']

    if title is None:
        text = participant['text_content']
        text_preview = text[:40] + '...' if len(text) > 40 else text
        title = f"{participant['participant_id']} - Trial {participant['trial_num']}\n\"{text_preview}\""

    fig, ax = plt.subplots(figsize=figsize)


    ax.set_xlim(0, canvas_width)
    ax.set_ylim(canvas_height, 0)

    # Calculate the actual extent of the text
    #max_y = df['y_position'].max() + 30  # add a small bottom margin

    #ax.set_xlim(0, canvas_width)
    #ax.set_ylim(max_y, 0)  # use text extent instead of canvas_height
    #ax.set_facecolor('#f5f5f5')


    colors_cmap = ['#ffffff', '#fff3e0', '#ffcc80', '#ff9800', '#f44336', '#b71c1c']
    cmap = LinearSegmentedColormap.from_list('duration', colors_cmap)

    max_dur = df['duration_ms'].max()
    min_dur = df['duration_ms'].min()
    dur_range = max_dur - min_dur if max_dur != min_dur else 1

    for _, row in df.iterrows():
        norm_dur = (row['duration_ms'] - min_dur) / dur_range
        color = cmap(norm_dur)

        rect = plt.Rectangle(
            (row['x_start'], row['y_position'] - 20),
            row['x_end'] - row['x_start'],
            24,
            color=color,
            zorder=1
        )
        ax.add_patch(rect)

        ax.text(
            (row['x_start'] + row['x_end']) / 2,
            row['y_position'],
            row['word'],
            ha='center', va='center',
            fontsize=9, zorder=2
        )

    sm = plt.cm.ScalarMappable(cmap=cmap,
                                norm=plt.Normalize(vmin=min_dur, vmax=max_dur))
    sm.set_array([])
    #plt.colorbar(sm, ax=ax, label='Duration (ms)')
    #plt.colorbar(sm, ax=ax, label='Duration (ms)', location='right', shrink=0.8, fraction=0.02, pad=0.02)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("bottom", size="5%", pad=-0.05)
    plt.colorbar(sm, cax=cax, label='Duration (ms)', orientation='horizontal')




    ax.set_title(title)
    ax.axis('off')
    plt.tight_layout()

    return fig