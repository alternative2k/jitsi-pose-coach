import subprocess
import asyncio
from pathlib import Path
from typing import List

class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"

    async def append_chunk_to_mp4(self, chunk_path: str, output_path: str, chunk_idx: int):
        """Simplified chunk handling using concat file approach"""
        try:
            if chunk_idx == 0:
                # First chunk - just save as MP4
                cmd = [
                    self.ffmpeg_path,
                    "-i", chunk_path,
                    "-c", "copy",
                    "-y",
                    output_path
                ]
            else:
                # For subsequent chunks, use concat demuxer
                # Create concat file
                concat_file = Path(output_path).parent / "concat.txt"

                if not concat_file.exists():
                    # Create initial concat with previous output
                    concat_file.write_text(f"file '{Path(output_path).name}'\n")

                # Add new chunk
                concat_content = concat_file.read_text()
                concat_content += f"file '{Path(chunk_path).name}'\n"
                concat_file.write_text(concat_content)

                # Merge using concat
                cmd = [
                    self.ffmpeg_path,
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    "-y",
                    output_path
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg error: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            print(f"Error processing video: {e}")
            return False

    async def merge_final_video(self, chunks: List[str], output_path: str) -> bool:
        """Merge all chunks into final MP4 (at session end)"""
        try:
            # Create concat file
            concat_file = Path(output_path).parent / "concat.txt"
            concat_lines = [
                f"file '{Path(chunk).resolve()}'"
                for chunk in sorted(chunks)
            ]
            concat_file.write_text("\n".join(concat_lines))

            # Merge
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-y",
                output_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg merge error: {stderr.decode()}")
                return False

            concat_file.unlink()
            return True

        except Exception as e:
            print(f"Error merging video: {e}")
            return False

    def reencode_chunk_to_mp4(self, input_path: str, output_path: str) -> bool:
        """Re-encode chunk to MP4 format"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-y",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"Error re-encoding: {e}")
            return False