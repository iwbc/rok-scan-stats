# This Python file uses the following encoding: utf-8

import os
import sys
import datetime
import argparse
import pyperclip
import csv
import portalocker
from android_auto_play_opencv import AapoManager

# Nox adbパス
ADB_PATH = "C:/Program Files/Nox/bin/"

# ランキングタップ位置（X軸）
RANKING_TAP_POS_X = 760
# ランキングタップ位置（Y軸、[1位,2位,3位,4位-998位,999位,1000位]）
RANKING_TAP_POS_Y = (280, 384, 485, 613, 713, 813)
# 撃破詳細タップ位置
KILL_DETAIL_TAP_POS = (1117, 352)
# 詳細情報タップ位置
PLAYER_DETAIL_TAP_POS = (386, 667)

aapo = None
template_dir_path = None
dir_path = None
img_dir_path = None
log_dir_path = None

current_rank: int = 0


def main():
    global aapo, template_dir_path, dir_path, img_dir_path, log_dir_path

    aapo = AapoManager(ADB_PATH)
    devices = aapo.adbl.devices

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--dir", type=str, default=datetime.datetime.now().strftime("%Y-%m-%d")
    )
    parser.add_argument("-s", "--start-rank", type=int, default=1)
    parser.add_argument("-e", "--end-rank", type=int, default=1000)
    args = parser.parse_args()

    print(f"\n===== {args.start_rank}位から{args.end_rank}位までキャプチャします。 =====\n")

    for i, device in enumerate(devices):
        if device == "":
            continue
        print(f"{i + 1}: {device}")

    try:
        deviceNo = int(input("\n操作するNoxPlayerの番号を入力してください: "))
        device = devices[deviceNo - 1]
        aapo.adbl.setdevice(device)
    except:
        print("無効な入力値です。処理を中止します。")
        sys.exit(1)

    template_dir_path = "templates/"
    dir_path = "data/" + args.dir + "/"
    img_dir_path = dir_path + "screenshots/"
    log_dir_path = dir_path + "logs/autocap/"

    os.makedirs(log_dir_path, exist_ok=True)

    start_rank: int = args.start_rank - 1
    end_rank: int = args.end_rank

    auto_capture(start_rank, end_rank)

    print("\n===== Done! =====")


def auto_capture(start: int, end: int):
    global current_rank

    for i in range(start, end):
        current_rank = i + 1

        print(f"\n===== {current_rank}位のキャプチャを開始します。 =====\n")

        # 総督情報表示
        if current_rank <= 3:
            aapo.touchPos(RANKING_TAP_POS_X, RANKING_TAP_POS_Y[i])
        elif current_rank == 999:
            aapo.touchPos(RANKING_TAP_POS_X, RANKING_TAP_POS_Y[4])
        elif current_rank == 1000:
            aapo.touchPos(RANKING_TAP_POS_X, RANKING_TAP_POS_Y[5])
        else:
            aapo.touchPos(RANKING_TAP_POS_X, RANKING_TAP_POS_Y[3])
        aapo.sleep(0.5)

        try:
            checkImg(template_dir_path + "player.png")
        except TimeoutError:
            err(f"{current_rank}位: 総督情報の表示に失敗しました。キャプチャをスキップします。 -> {current_rank}.png")
            if aapo.chkImg(template_dir_path + "ranking.png"):
                aapo.swipeTouchPos(
                    RANKING_TAP_POS_X,
                    RANKING_TAP_POS_Y[3],
                    RANKING_TAP_POS_X,
                    RANKING_TAP_POS_Y[3] - 100,
                    1000,
                )
                continue
            else:
                err(f"ランキングの表示に失敗しました。処理を中止します。 -> {current_rank}.png")
                sys.exit(1)

        # 撃破詳細表示・キャプチャ
        aapo.touchPos(KILL_DETAIL_TAP_POS[0], KILL_DETAIL_TAP_POS[1])
        aapo.sleep(0.25)

        try:
            checkImg(template_dir_path + "kill.png")
        except TimeoutError:
            err(f"{current_rank}位: 撃破詳細の表示に失敗しました。キャプチャをスキップします。 -> {current_rank}.png")
            returnToRankingScreen()
            continue

        aapo.imgSave(img_dir_path + str(current_rank) + "a.png")

        # 詳細情報表示・キャプチャ
        aapo.touchPos(PLAYER_DETAIL_TAP_POS[0], PLAYER_DETAIL_TAP_POS[1])
        aapo.sleep(0.5)

        try:
            checkImg(template_dir_path + "detail.png")
        except TimeoutError:
            err(f"{current_rank}位: 詳細情報の表示に失敗しました。キャプチャをスキップします。 -> {current_rank}.png")
            returnToRankingScreen()
            continue

        aapo.imgSave(img_dir_path + str(current_rank) + "b.png")

        # 総督名保存
        with portalocker.Lock(
            img_dir_path + "names.tsv",
            "a+",
            encoding="utf_8",
            newline="",
            timeout=60,
        ) as fh:
            fh.seek(0)
            aapo.touchImg(template_dir_path + "copy.png")
            aapo.sleep(0.1)
            names = list(csv.reader(fh, delimiter="\t"))
            names.append([str(current_rank), pyperclip.paste()])
            fh.truncate(0)
            fh.seek(0)
            csv.writer(fh, delimiter="\t").writerows(
                sorted(names, key=lambda x: int(x[0]))
            )

        # ランキングまで戻る
        returnToRankingScreen()


def checkImg(img_path: str):
    timer = 0
    while True:
        aapo.screencap()
        if aapo.chkImg(img_path):
            break
        elif timer >= 4:
            raise TimeoutError
        else:
            timer += 1
            aapo.sleep(1)


def returnToRankingScreen():
    timer = 0
    while True:
        aapo.screencap()
        if aapo.chkImg(template_dir_path + "ranking.png"):
            break
        elif timer >= 4:
            err(f"ランキングの表示に失敗しました。処理を中止します。 -> {current_rank}.png")
            sys.exit(1)
        else:
            aapo.touchImg(template_dir_path + "close.png")
            timer += 1
            aapo.sleep(1)


def err(message: str):
    print(message)
    with portalocker.Lock(
        log_dir_path + "error.log", "a", encoding="utf_8", timeout=60
    ) as fh:
        fh.write(message + "\n")
    aapo.imgSave(log_dir_path + str(current_rank) + ".png")


if __name__ == "__main__":
    main()
