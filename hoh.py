# This Python file uses the following encoding: utf-8

import os
import csv
import sys
import time
import argparse
import cv2
import numpy as np
import pyocr
from joblib import Parallel, delayed
from typing import TypeAlias, Literal, TypedDict, get_args
import utils.image
from utils.builder import Builder


class Result(TypedDict):
    id: str
    dead: "Dead"
    user_input_dead: "Dead"


TroopTypes: TypeAlias = Literal[
    "T5 Inf",
    "T5 Cav",
    "T5 Arch",
    "T5 Siege",
    "T4 Inf",
    "T4 Cav",
    "T4 Arch",
    "T4 Siege",
]

Dead: TypeAlias = dict[
    TroopTypes,
    int,
]

ocr_tool = None

base_path: str = None
templates_dir_path: str = None
data_dir_path: str = None

troop_icon_images: dict[str, list] = {}
troop_types: list[TroopTypes] = list(get_args(TroopTypes))


def main():
    global ocr_tool, base_path, templates_dir_path, data_dir_path, troop_icon_images

    startTime = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=str)
    parser.add_argument("-j", "--jobs", type=int, default=-1)
    args = parser.parse_args()

    ocr_tools = pyocr.get_available_tools()
    if len(ocr_tools) == 0:
        print("OCRツールが見つかりません。")
        sys.exit(1)
    ocr_tool = ocr_tools[0]

    base_path = os.path.dirname(__file__)
    templates_dir_path = os.path.join(base_path, "templates/hoh")
    data_dir_path = os.path.join(base_path, "data", args.dir)

    troop_icon_images = {
        type: [
            # 隠しファイル（.DS_Storeなど）を除いたファイル一覧を取得し、読み込む
            # 特徴点を検出しやすくなるよう黒の余白を追加する
            cv2.copyMakeBorder(
                cv2.imread(os.path.join(templates_dir_path, type, name)),
                50,
                50,
                50,
                50,
                cv2.BORDER_CONSTANT,
                value=(0, 0, 0),
            )
            for name in os.listdir(os.path.join(templates_dir_path, type))
            if not name.startswith(".")
        ]
        for type in troop_types
    }

    with open(
        os.path.join(data_dir_path, "hoh/ids.tsv"), "r", encoding="utf_8", newline=""
    ) as fh:
        tsv_rows = list(csv.reader(fh, delimiter="\t"))

    parallel_results: list[Result | None] = Parallel(n_jobs=args.jobs)(
        delayed(parallel_func)(row) for row in tsv_rows
    )
    results: list[Result] = [
        result for result in parallel_results if result is not None
    ]

    with open(
        os.path.join(data_dir_path, "hoh.tsv"), "w", encoding="utf_8", newline=""
    ) as fh:
        data = [["ID", *troop_types]]
        {data.append([result["id"], *result["dead"].values()]) for result in results}
        csv.writer(fh, delimiter="\t").writerows(data)

    endTime = time.time()
    print(f"\n処理時間：{endTime - startTime}")


def parallel_func(row: list[str]):
    id = str(row[0])
    image_path = os.path.join(data_dir_path, f"hoh/{id}")

    if os.path.exists(image_path + ".png"):
        image_path += ".png"
    elif os.path.exists(image_path + ".jpg"):
        image_path += ".jpg"
    else:
        return None

    detail_image = crop_detail_popup(image_path)

    detector = cv2.AKAZE_create()
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

    dead = {troop_type: 0 for troop_type in troop_types}
    result: Result = {"id": id, "dead": dead, "user_input_dead": dead}

    if detail_image is not None:
        troop_icon_contours = detect_troop_icon(detail_image)
        determined_troop_types = []

        for contour in troop_icon_contours:
            troop_type = determine_troop_type(
                detector,
                matcher,
                detail_image,
                troop_icon_images,
                contour,
                determined_troop_types,
            )
            if troop_type:
                determined_troop_types.append(troop_type)
                dead = ocr(detail_image, contour)
                result["dead"][troop_type] = dead

        print(
            f"{result['id']} {' '.join(str(dead) for dead in result['dead'].values())}"
        )
        return result


def crop_detail_popup(image_path: str):
    image = cv2.imread(image_path)

    mask = cv2.inRange(image, np.array([200, 200, 200]), np.array([255, 255, 255]))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0
    max_rect = None
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area:
            max_area = area
            max_rect = cv2.boundingRect(contour)

    if max_rect is not None:
        x, y, w, h = max_rect
        cropped_image = image[y : y + h, x : x + w]

        aspect_ratio = h / w
        cropped_image = cv2.resize(cropped_image, (1200, int(1200 * aspect_ratio)))
        cropped_image = cropped_image[0 : int(1200 * aspect_ratio), 0:1180]

        if max_area * 1200 / w >= 150000:
            return cropped_image


def detect_troop_icon(detail_image: cv2.Mat):
    binary_image = cv2.inRange(
        detail_image, np.array([200, 200, 200]), np.array([255, 255, 255])
    )
    binary_image = cv2.bitwise_not(binary_image)
    contours, _ = cv2.findContours(
        binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = list(filter(lambda x: cv2.contourArea(x) > 6000, contours))
    contours.sort(
        key=lambda ctr: cv2.boundingRect(ctr)[0]
        + int(cv2.boundingRect(ctr)[1] / 100) * 100 * detail_image.shape[1]
    )

    return contours


def determine_troop_type(
    detector,
    matcher,
    detail_image: cv2.Mat,
    troop_icon_images: dict[str, list[cv2.Mat]],
    contour,
    determined_troop_types: list,
):
    mask = np.zeros(detail_image.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, color=255, thickness=-1)
    _, detail_des = detector.detectAndCompute(detail_image, mask)

    max_good_matches = []
    determined_troop_type = None

    for troop_type in troop_types:
        # 他の項目で判定された兵種はスキップ
        if troop_type in determined_troop_types:
            continue

        for troop_icon_image in troop_icon_images[troop_type]:
            _, troop_icon_des = detector.detectAndCompute(troop_icon_image, None)
            matches = matcher.knnMatch(troop_icon_des, detail_des, k=2)

            ratio = 0.7
            good_matches = []
            for m, n in matches:
                if m.distance < ratio * n.distance:
                    good_matches.append([m])

            if len(good_matches) >= 8 and len(good_matches) > len(max_good_matches):
                max_good_matches = good_matches
                determined_troop_type = troop_type

    return determined_troop_type


def ocr(detail_image: cv2.Mat, contour):
    x, y, _, h = cv2.boundingRect(contour)
    corrected_image = utils.image.correct(
        utils.image.cv2pil(detail_image),
        crop_range=(x + 155, y, x + 350, y + h),
        threshold=50,
        invert=False,
        brightness=1.2,
        contrast=1.2,
    )
    dead = ocr_tool.image_to_string(corrected_image, lang="eng", builder=Builder())

    return int(dead.replace(",", ""))


if __name__ == "__main__":
    main()
