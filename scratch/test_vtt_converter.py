import re

def convert_vtt_to_srt(vtt_content: str) -> str:
    lines = vtt_content.splitlines()
    srt_lines = []
    cue_counter = 1
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            i += 1
            continue
            
        if "-->" in line:
            # Clean timestamp line
            time_match = re.search(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})", line)
            if time_match:
                start_t, end_t = time_match.group(1), time_match.group(2)
                # Format to HH:MM:SS,mmm
                if len(start_t.split(":")[0]) == 1:
                    start_t = "0" + start_t
                if ":" not in start_t[:-7]: # mm:ss
                    start_t = "00:" + start_t
                if len(end_t.split(":")[0]) == 1:
                    end_t = "0" + end_t
                if ":" not in end_t[:-7]:
                    end_t = "00:" + end_t
                    
                start_t = start_t.replace(".", ",")
                end_t = end_t.replace(".", ",")
                
                srt_lines.append(str(cue_counter))
                cue_counter += 1
                srt_lines.append(f"{start_t} --> {end_t}")
                
                i += 1
                while i < len(lines) and lines[i].strip():
                    # Strip VTT formatting tags like <v English> or <b>
                    clean_text = re.sub(r"<[^>]+>", "", lines[i].strip())
                    if clean_text:
                        srt_lines.append(clean_text)
                    i += 1
                srt_lines.append("")
        i += 1
        
    return "\n".join(srt_lines)

sample_vtt = """WEBVTT

NOTE This is a sample note

00:00:01.500 --> 00:00:04.200 align:start position:10%
<v Host>Hello world!</v>
This is line two.

00:00:05.100 --> 00:00:08.300
Sample subtitle line.
"""

print(convert_vtt_to_srt(sample_vtt))
