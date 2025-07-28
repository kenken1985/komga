This is a customized version of Komga, a Manga reading server. The customization aims at adding a "PUSH TO KINDLE BUTTON" which add the following function:

1) The WEBUI pass the file path(s) to the python code (komga_custom/push_to_kindle.py)
2) If cbr is detected, it convert to a tmp cbz
3) If AVIF and WEBP (image format not supported by Kindle) is detected inside the cbz, it convert those image to jpg and creat a tmp cbz
4) It push the (tmp) files to remote Kindle device using SCP

Currently, the code is in production status. The following additional function is planned.

1) If multiple files is pushed at once, it will create a folder named as the series name, else, it will push the single files to a folder named "New Volume"
2) It add the PUSH TO KINDLE button to the menu that appear when multiple books in same series is selected in WEBUI.
3) Resize to fill addition margin in black color so that it fit the aspect ratio of kindle paperwhite (1246 x 1648)
4) Refactor the python code into using native Ktolin, and remove the python part from Dockerfile.