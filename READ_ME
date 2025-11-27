# NFS Hot Pursuit Remastered Lobby Assistant

This is a utility tool based on Python and Computer Vision, designed specifically for *Need for Speed: Hot Pursuit Remastered*. The code is heavily commented, making it an excellent reference for script kiddies or beginners looking to get started with Python and Computer Vision.

**⚠️ Disclaimer: This script is solely for assisting with "auto-matchmaking" and "menu car selection". It does NOT contain any cheating features such as auto-driving, aimbot, or memory modification. It is intended only to help players save time on repetitive menu operations. Any infringing content will be removed immediately upon notice.**

## ✨ Key Features

* **Visual Recognition**: Uses OpenCV grayscale matching technology to accurately identify UI states, ignoring day/night lighting changes in the game.
* **OBS Compatibility**: Captures footage via OBS Virtual Camera, perfectly supporting the game's "Exclusive Fullscreen" mode (solving the black screen issue with standard screenshots).
* **Auto-Reconnect**: Automatically detects network disconnections or matchmaking failures and searches for a new lobby.
* **Custom Car Selection**: Configurable logic allowing you to set custom key press counts for each car class.
* **Smart Anti-Interference**:
    * **Manual Takeover**: During auto-selection, if you press the `Left` or `Right` arrow keys, the script immediately stops and hands control back to you.
    * **Anti-Mistouch Sleep**: After confirming a car, the script automatically enters a 40-second Deep Sleep (visual detection off) to prevent accidental inputs during game transitions.
* **Resource Efficiency**: Offers "Run Mode", "Sleep Mode", and "Deep Sleep Mode" with extremely low CPU/GPU usage.

## 🛠️ Requirements

1.  **Python 3.10+**
2.  **OBS Studio** (Required for Virtual Camera)
3.  Game Resolution: **1920x1080** or **2560x1440** (Other resolutions have not been tested).

## 📂 Directory Structure

Please ensure your folder structure looks like this before running:

```
nfs-autopilot/
│
├── assets/                 <-- [Required] Game UI screenshots (.png)
│   ├── main_page.png
│   ├── online_main_page.png
│   ├── policecar_a.png
│   └── ... (approx. 16 images)
│
├── nfs_bot.py              <-- Core script
├── requirements.txt        <-- Dependencies
└── README.md               <-- Documentation
```

## 🚀 Installation
Download this project: Click Code -> Download ZIP in the top right corner and unzip it locally.

Install Dependencies: Open a terminal (CMD or PowerShell) in the unzipped directory and run:

```
pip install -r requirements.txt
```
Prepare Assets:

The script relies on game screenshots located in the assets folder.

Note: Please ensure the assets folder contains the corresponding game UI screenshots, and filenames match those defined in the code.

## 📝 Custom Car Configuration
You can open nfs_bot.py and modify the car selection logic in the CAR_SELECTION_CONFIG section at the top.

Number meaning: Represents how many times the script automatically presses the "Right Arrow" key for that category.

0: Represents pressing no arrow keys and directly selecting the first car with Space.


# Car Selection Configuration
```
CAR_SELECTION_CONFIG = {
    "POLICE": {
        "a": 7,  # Police Class A (Special Response Unit): Vehicle at 7 right clicks
        "b": 6,  # Police Class B (Traffic Police Unit): Vehicle at 6 right clicks
        "c": 10,
        "d": 1,
        "e": 0
    },
    "RACER": {
        "a": 7,  # Racer Class A (Exotic): Vehicle at 7 right clicks
        "b": 5,  # Racer Class B (Dream): Vehicle at 5 right clicks
        "c": 16,
        "d": 12,
        "e": 1
    }
}
```
## 🕹️ Script Usage & Logic
* **Preparation:**

Start OBS, add the game source, and enable "Virtual Camera".

Ensure your network connection is stable.

Run the script: python nfs_bot.py.

* **Startup:**

Navigate the game to the Main Page.

Press the number key 7 to activate the script.

* **Operational Logic:**

Auto-Join: Upon recognizing the main page, the script automatically navigates to "Multiplayer Mode".

Auto-Retry: If joining fails due to network issues and returns to the multiplayer main menu, the script detects the state and retries automatically.

Auto-Select Car: Once in a lobby, the script selects your default vehicle based on the pre-configured settings (see above).

Random Paint: After selecting a car, the script automatically picks a random paint color and confirms.

* **Advanced Modification:**

The code follows a modular design. If you wish to select a specific custom paint instead of a random one, please modify the sequence_color_confirm_random function logic in the code yourself.

## ⌨️ Controls
7: Run Mode

9: Sleep Mode

0: Deep Sleep

V: Toggle Debug Window

## 📄 License
MIT License.

## Note
If this project helps you, please leave a Star :)
