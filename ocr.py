# This Python file uses the following encoding: utf-8

import os
import sys
import time
import argparse
import csv
import re
from joblib import Parallel, delayed
import portalocker
import pyocr
import pyocr.builders
from PIL import Image, ImageOps, ImageEnhance

# 同盟タグの切り抜き範囲
ALLIANCE_CROP_RANGE = (644, 365, 763, 396)

# IDの切り抜き範囲
ID_CROP_RANGE = (735, 236, 880, 268)

# 撃破数の切り抜き範囲
# (
#   (T1撃破数範囲),
#   (T2撃破数範囲),
#   ...
# )
KILL_CROP_RANGES = (
    (862, 599, 1067, 625),
    (862, 643, 1067, 669),
    (862, 687, 1067, 713),
    (862, 732, 1067, 758),
    (862, 776, 1067, 802),
)

# 撃破ポイントの切り抜き範囲
# (
#   (T1撃破数範囲),
#   (T2撃破数範囲),
#   ...
# )
KILL_POINT_CROP_RANGES = (
    (1211, 599, 1415, 625),
    (1211, 643, 1415, 669),
    (1211, 687, 1415, 713),
    (1211, 732, 1415, 758),
    (1211, 776, 1415, 802),
)

# 撃破ポイント係数
# (T1, T2, T3, T4, T5)
KILL_POINT_COEFFICIENTS = (0.2, 2, 4, 10, 20)

# 戦力の切り抜き範囲
POWER_CROP_RANGE = (809, 141, 1009, 173)

# 過去最大戦力の切り抜き範囲
HIGHEST_POWER_CROP_RANGE = (1103, 266, 1303, 296)

# 戦死数の切り抜き範囲
DEAD_CROP_RANGE = (1103, 450, 1303, 480)

# 資源援助数の切り抜き範囲
RSS_CROP_RANGE = (1053, 680, 1303, 710)

tool = None
dir_path: str = None
img_dir_path: str = None
log_dir_path: str = None


class Builder(pyocr.builders.TextBuilder):
    def __init__(self, whitelist: str, tesseract_layout: int = 6):
        super(Builder, self).__init__(tesseract_layout)
        self.tesseract_configs += ["-c", "tessedit_char_whitelist=" + whitelist]


def main():
    startTime = time.time()

    global tool, dir_path, img_dir_path, log_dir_path

    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=str)
    parser.add_argument("-j", "--jobs", type=int, default=-2)
    args = parser.parse_args()

    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("OCRツールが見つかりません。")
        sys.exit(1)
    tool = tools[0]

    dir_path = "data/" + args.dir + "/"
    img_dir_path = dir_path + "screenshots/"
    log_dir_path = dir_path + "logs/ocr/"

    data = []

    os.makedirs(log_dir_path, exist_ok=True)

    with open(img_dir_path + "names.tsv", "r", encoding="utf_8", newline="") as fh:
        names = list(csv.reader(fh, delimiter="\t"))
        data += Parallel(n_jobs=args.jobs)(
            delayed(ocr_images)(rank, name) for rank, name in names
        )

    with open(dir_path + "data.tsv", "w", encoding="utf_8", newline="") as fh:
        data = sorted(data, key=lambda x: int(x[0]))
        data.insert(
            0,
            (
                "Rank",
                "Name",
                "ID",
                "Alliance",
                "Power",
                "Highest Power",
                "T1 Kills",
                "T2 Kills",
                "T3 Kills",
                "T4 Kills",
                "T5 Kills",
                "Dead",
                "RSS",
            ),
        )
        csv.writer(fh, delimiter="\t").writerows(data)

    endTime = time.time()
    print(f"\n処理時間：{endTime - startTime}")


def ocr_images(rank: str, name: str):
    img_a = Image.open(img_dir_path + rank + "a.png")
    if img_a.mode == "RGBA":
        img_a = img_a.convert("RGB")

    img_b = Image.open(img_dir_path + rank + "b.png")
    if img_b.mode == "RGBA":
        img_b = img_b.convert("RGB")

    # ID
    id_img = correct_image(img_a, ID_CROP_RANGE, threshold=50, contrast=5, brightness=2)
    id = ocr_image(id_img, whitelist="0123456789)")
    id = re.sub("\)$", "", id)
    if id == "":
        err(
            f"{rank}位 - {name}: 「ID」の読み取りに失敗しました。 -> {rank}-id.png",
            [(f"{rank}-id.png", id_img)],
        )

    # 同盟タグ
    alliance_img = correct_image(
        img_a, ALLIANCE_CROP_RANGE, scale=5, contrast=1.3, brightness=2
    )
    alliance = ocr_image(
        alliance_img,
        whitelist=f"[]0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`~!@#&-_=+;:'\",<>/",
    )
    alliance = re.match(r"^\[(.{3,4})\]", alliance)
    if alliance is None:
        alliance = ""
    else:
        alliance = alliance.group(1)

    # 撃破
    kills = []
    for i, (
        kill_crop_range,
        kill_point_crop_range,
        kill_point_coefficient,
    ) in enumerate(
        zip(KILL_CROP_RANGES, KILL_POINT_CROP_RANGES, KILL_POINT_COEFFICIENTS)
    ):
        kill_img = correct_image(
            img_a,
            kill_crop_range,
            threshold=50,
            invert=False,
            brightness=1.2,
            contrast=1.2,
        )
        kill = ocr_image(kill_img)
        kill_p_img = correct_image(
            img_a,
            kill_point_crop_range,
            threshold=50,
            invert=False,
            brightness=1.2,
            contrast=1.2,
        )
        kill_p = ocr_image(kill_p_img)

        kill = kill.replace(",", "")
        kill_p = kill_p.replace(",", "")

        kill_img_file_name = rank + "-t" + str(i + 1) + "-kill.png"
        kill_p_img_file_name = rank + "-t" + str(i + 1) + "-kill-point.png"

        if kill == "":
            err(
                f"{rank}位 - {name}: 「T{i + 1}撃破数」の読み取りに失敗しました。 -> {kill_img_file_name}, {kill_p_img_file_name}",
                [(kill_img_file_name, kill_img), (kill_p_img_file_name, kill_p_img)],
            )
        elif abs(int(kill) * kill_point_coefficient - int(kill_p)) > 1:
            err(
                f"{rank}位 - {name}: 「T{i + 1}撃破数」を正しく読み取りできなかった可能性があります。OCRの結果は撃破数「{kill}」、撃破ポイント「{kill_p}」です。 -> {kill_img_file_name}, {kill_p_img_file_name}",
                [(kill_img_file_name, kill_img), (kill_p_img_file_name, kill_p_img)],
            )

        kills.append(kill)

    # 戦力
    power_img = correct_image(
        img_b, POWER_CROP_RANGE, threshold=50, brightness=2, contrast=1.2
    )
    power = ocr_image(power_img)
    power = power.replace(",", "")
    if power == "":
        err(
            f"{rank}位 - {name}: 「戦力」の読み取りに失敗しました。 -> {rank}-power.png",
            [(f"{rank}-power.png", power_img)],
        )

    # 過去最大戦力
    hpower_img = correct_image(img_b, HIGHEST_POWER_CROP_RANGE, brightness=1.3, contrast=1.8)
    hpower = ocr_image(hpower_img)
    hpower = hpower.replace(",", "")
    if hpower == "":
        err(
            f"{rank}位 - {name}: 「過去最大戦力」の読み取りに失敗しました。 -> {rank}-hpower.png",
            [(f"{rank}-dead.png", hpower_img)],
        )
    elif int(power) > int(hpower):
        err(
            f"{rank}位 - {name}: 「戦力」または「過去最大戦力」を正しく読み取りできなかった可能性があります。OCRの結果は戦力「{power}」、過去最大戦力「{hpower}」です。 -> {rank}-power.png, {rank}-hpower.png",
            [(f"{rank}-power.png", power_img), (f"{rank}-hpower.png", hpower_img)],
        )

    # 戦死
    dead_img = correct_image(img_b, DEAD_CROP_RANGE, brightness=1.3, contrast=1.8)
    dead = ocr_image(dead_img)
    dead = dead.replace(",", "")
    if dead == "":
        err(
            f"{rank}位 - {name}: 「戦死数」の読み取りに失敗しました。 -> {rank}-dead.png",
            [(f"{rank}-dead.png", dead_img)],
        )

    # 資源援助
    rss_img = correct_image(img_b, RSS_CROP_RANGE, brightness=1.3, contrast=1.8)
    rss = ocr_image(rss_img)
    rss = rss.replace(",", "")
    if rss == "":
        err(
            f"{rank}位 - {name}: 「資源援助数」の読み取りに失敗しました。 -> {rank}-rss.png",
            [(f"{rank}-rss.png", rss_img)],
        )

    print(
        f"{rank} {name} {id} {alliance} {power} {hpower} {kills[0]} {kills[1]} {kills[2]} {kills[3]} {kills[4]} {dead} {rss}"
    )

    return (
        rank,
        name,
        id,
        alliance,
        power,
        hpower,
        kills[0],
        kills[1],
        kills[2],
        kills[3],
        kills[4],
        dead,
        rss,
    )


def correct_image(
    img: Image.Image,
    crop_range: tuple,
    threshold: int = 0,
    threshold_max: int = -1,
    invert: bool = True,
    scale: float = 1,
    contrast: float = 1,
    brightness: float = 1,
) -> Image.Image:
    tmp = img.crop(crop_range)
    tmp = ImageOps.invert(tmp) if invert else tmp
    tmp = tmp.convert("L")
    tmp = tmp.resize((round(tmp.width * scale), round(tmp.height * scale))) if scale != 1 else tmp
    tmp = ImageEnhance.Contrast(tmp).enhance(contrast) if contrast != 1 else tmp
    tmp = ImageEnhance.Brightness(tmp).enhance(brightness) if brightness != 1 else tmp
    if threshold == 0:
        pass
    elif threshold_max == -1:
        tmp = tmp.point(lambda x: 0 if x < threshold else x)
    else:
        tmp = tmp.point(lambda x: 0 if x < threshold else threshold_max)
    return tmp


def ocr_image(img: Image, whitelist: str = "0123456789,") -> str:
    result = tool.image_to_string(img, lang="eng", builder=Builder(whitelist))
    return result


def err(message: str, imgs: list[tuple[str, Image.Image]] = {}):
    print(message)

    for file_name, img in imgs:
        img.save(log_dir_path + file_name)

    with portalocker.Lock(
        log_dir_path + "error.log", "a", encoding="utf_8", timeout=60
    ) as fh:
        fh.write(message + "\n")


if __name__ == "__main__":
    main()
