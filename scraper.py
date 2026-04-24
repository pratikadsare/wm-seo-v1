import json
import re
import time
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

IMAGE_DOMAIN = "i5.walmartimages.com"
BAD_IMAGE_WORDS = [
    "sprite", "icon", "logo", "badge", "rating", "star", "stars", "review",
    "avatar", "profile", "seller", "brand-logo", "swatch", "variant", "variation",
    "placeholder", "transparent", "spark", "walmart",
]

DEFAULT_FIELDS = [
    "Item ID", "Title", "Brand", "Price", "Seller", "Availability", "Rating",
    "Review Count", "Main Image", "Additional Images", "Bullet Points",
    "Description", "Specifications", "Ingredients", "Warnings", "Category",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " | ".join(clean_text(v) for v in value if clean_text(v))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_first_key(obj: Any, keys: List[str]) -> Any:
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] not in (None, "", [], {}):
                return obj[key]
        for value in obj.values():
            found = find_first_key(value, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_first_key(item, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def find_all_by_key(obj: Any, keys: List[str]) -> List[Any]:
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in keys and value not in (None, "", [], {}):
                found.append(value)
            found.extend(find_all_by_key(value, keys))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_all_by_key(item, keys))
    return found


def extract_next_data(soup: BeautifulSoup) -> Dict[str, Any]:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return {}
    try:
        return json.loads(script.get_text(strip=False))
    except Exception:
        return {}


def extract_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    output = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.get_text(strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
            if isinstance(data, list):
                output.extend([x for x in data if isinstance(x, dict)])
            elif isinstance(data, dict):
                output.append(data)
        except Exception:
            continue
    return output


def get_item_id(url: str, data: Dict[str, Any]) -> str:
    match = re.search(r"/ip/(?:[^/]+/)?(\d+)", url)
    if match:
        return match.group(1)
    found = find_first_key(data, ["usItemId", "itemId", "productId"])
    return clean_text(found)


def normalize_image_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace("\\u002F", "/").replace("\\/", "/")
    url = url.split("?")[0]
    return url


def is_product_image(url: str) -> bool:
    url = normalize_image_url(url)
    if not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    if IMAGE_DOMAIN not in parsed.netloc:
        return False
    lower = url.lower()
    if lower.endswith(".png") or lower.endswith(".svg") or lower.endswith(".gif"):
        return False
    if any(word in lower for word in BAD_IMAGE_WORDS):
        return False
    if not any(ext in lower for ext in [".jpeg", ".jpg", ".webp"]):
        return False
    if "/asr/" not in lower and "/seo/" not in lower:
        return False
    return True


def extract_images(data: Dict[str, Any], selected_fields: List[str]) -> Dict[str, str]:
    image_values = []
    for key in ["imageInfo", "images", "image", "thumbnailUrl", "productImageUrl"]:
        image_values.extend(find_all_by_key(data, [key]))

    urls = []
    json_text = json.dumps(image_values, ensure_ascii=False)
    urls.extend(re.findall(r"https://i5\.walmartimages\.com/[^\"'\s]+", json_text))

    for value in image_values:
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, dict):
            for k in ["url", "thumbnailUrl", "largeUrl", "mainImageUrl"]:
                if value.get(k):
                    urls.append(str(value.get(k)))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict):
                    for k in ["url", "thumbnailUrl", "largeUrl", "mainImageUrl"]:
                        if item.get(k):
                            urls.append(str(item.get(k)))

    cleaned = []
    for url in urls:
        norm = normalize_image_url(url)
        if is_product_image(norm) and norm not in cleaned:
            cleaned.append(norm)

    main_image = cleaned[0] if cleaned else ""
    additional = cleaned[1:]
    return {
        "Main Image": main_image if "Main Image" in selected_fields else "",
        "Additional Images": " | ".join(additional) if "Additional Images" in selected_fields else "",
    }


def extract_specs(data: Dict[str, Any]) -> str:
    candidates = []
    for key in ["specifications", "productHighlights", "details", "keyAttributes"]:
        candidates.extend(find_all_by_key(data, [key]))

    rows = []
    for cand in candidates:
        if isinstance(cand, list):
            for item in cand:
                if isinstance(item, dict):
                    name = clean_text(item.get("name") or item.get("key") or item.get("title"))
                    value = clean_text(item.get("value") or item.get("values") or item.get("description"))
                    if name and value and len(value) < 500:
                        rows.append(f"{name}: {value}")
        elif isinstance(cand, dict):
            for key, value in cand.items():
                key_text = clean_text(key)
                value_text = clean_text(value)
                if key_text and value_text and len(value_text) < 500:
                    rows.append(f"{key_text}: {value_text}")

    clean_rows = []
    for row in rows:
        low = row.lower()
        if "ai" in low and "summary" in low:
            continue
        if row not in clean_rows:
            clean_rows.append(row)
    return " | ".join(clean_rows[:80])


def extract_bullets(data: Dict[str, Any]) -> str:
    candidates = []
    for key in ["shortDescription", "longDescription", "productHighlights", "keyFeatures", "features"]:
        candidates.extend(find_all_by_key(data, [key]))

    bullets = []
    for cand in candidates:
        if isinstance(cand, list):
            for item in cand:
                if isinstance(item, dict):
                    text = clean_text(item.get("name") or item.get("value") or item.get("description") or item.get("title"))
                else:
                    text = clean_text(item)
                if text:
                    bullets.append(text)
        else:
            text = clean_text(cand)
            parts = re.split(r"(?:\u2022|•|\n|</li>|<li>)", text)
            bullets.extend(clean_text(p) for p in parts if clean_text(p))

    clean_bullets = []
    for bullet in bullets:
        low = bullet.lower()
        if any(skip in low for skip in ["ai-generated", "ai generated", "summary", "customers say"]):
            continue
        if 4 <= len(bullet) <= 700 and bullet not in clean_bullets:
            clean_bullets.append(bullet)
    return " | ".join(clean_bullets[:25])


def extract_description(data: Dict[str, Any]) -> str:
    candidates = find_all_by_key(data, ["longDescription", "description", "productDescription"])
    for cand in candidates:
        text = clean_text(cand)
        low = text.lower()
        if text and "ai-generated" not in low and "customers say" not in low and len(text) > 20:
            return text[:5000]
    return ""


def extract_by_keywords(data: Dict[str, Any], keywords: List[str]) -> str:
    json_text = json.dumps(data, ensure_ascii=False)
    clean_json = clean_text(json_text)
    for keyword in keywords:
        pattern = rf"{keyword}[:\s]+([^|]{{10,1500}})"
        match = re.search(pattern, clean_json, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return ""


def scrape_walmart_product(sku: str, url: str, selected_fields: List[str], delay_seconds: float = 0.0) -> Dict[str, str]:
    result = {
        "SKU": sku,
        "Walmart URL": url,
        "Status": "Success",
        "Error": "",
    }
    for field in selected_fields:
        result[field] = ""

    try:
        if delay_seconds:
            time.sleep(delay_seconds)

        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            result["Status"] = "Failed"
            result["Error"] = f"HTTP {response.status_code}"
            return result

        soup = BeautifulSoup(response.text, "lxml")
        next_data = extract_next_data(soup)
        json_ld = extract_json_ld(soup)
        combined = {"next_data": next_data, "json_ld": json_ld}

        title = clean_text(find_first_key(combined, ["name", "title", "productName"]))
        if not title:
            h1 = soup.find("h1")
            title = clean_text(h1.get_text(" ")) if h1 else ""

        if "Item ID" in selected_fields:
            result["Item ID"] = get_item_id(url, combined)
        if "Title" in selected_fields:
            result["Title"] = title
        if "Brand" in selected_fields:
            brand = find_first_key(combined, ["brand", "brandName"])
            if isinstance(brand, dict):
                brand = brand.get("name")
            result["Brand"] = clean_text(brand)
        if "Price" in selected_fields:
            price = find_first_key(combined, ["price", "currentPrice", "priceString"])
            if isinstance(price, dict):
                price = price.get("price") or price.get("priceString")
            result["Price"] = clean_text(price)
        if "Seller" in selected_fields:
            seller = find_first_key(combined, ["sellerName", "sellerDisplayName", "seller"])
            if isinstance(seller, dict):
                seller = seller.get("name") or seller.get("displayName")
            result["Seller"] = clean_text(seller)
        if "Availability" in selected_fields:
            availability = find_first_key(combined, ["availabilityStatus", "availability", "stockStatus"])
            page_text = soup.get_text(" ", strip=True).lower()
            if not availability:
                if "out of stock" in page_text:
                    availability = "Out of stock"
                elif "add to cart" in page_text:
                    availability = "Available"
            result["Availability"] = clean_text(availability)
        if "Rating" in selected_fields:
            result["Rating"] = clean_text(find_first_key(combined, ["averageRating", "ratingValue", "rating"]))
        if "Review Count" in selected_fields:
            result["Review Count"] = clean_text(find_first_key(combined, ["numberOfReviews", "reviewCount", "ratingCount"]))
        if "Main Image" in selected_fields or "Additional Images" in selected_fields:
            result.update(extract_images(combined, selected_fields))
        if "Bullet Points" in selected_fields:
            result["Bullet Points"] = extract_bullets(combined)
        if "Description" in selected_fields:
            result["Description"] = extract_description(combined)
        if "Specifications" in selected_fields:
            result["Specifications"] = extract_specs(combined)
        if "Ingredients" in selected_fields:
            ingredients = extract_by_keywords(combined, ["Ingredients", "Ingredient"])
            result["Ingredients"] = ingredients
        if "Warnings" in selected_fields:
            warnings = extract_by_keywords(combined, ["Warnings", "Warning", "Caution"])
            result["Warnings"] = warnings
        if "Category" in selected_fields:
            category = find_first_key(combined, ["categoryPath", "category", "productType"])
            result["Category"] = clean_text(category)

        if not title and "Title" in selected_fields:
            result["Status"] = "Partial"
            result["Error"] = "Title not found. Walmart may have blocked or changed the page data."

        return result

    except Exception as exc:
        result["Status"] = "Failed"
        result["Error"] = str(exc)
        return result
