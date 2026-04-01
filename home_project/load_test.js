import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "45s",
};

const predictUrl = "http://localhost:8003/predict";
const predictPayload = JSON.stringify({
  seller_id: 10,
  is_verified_seller: true,
  item_id: 1001,
  name: "Нагрузочный товар",
  description: "Описание объявления для генерации метрик модерации",
  category: 3,
  images_qty: 2,
});

export default function () {
  const res = http.post(predictUrl, predictPayload, {
    headers: { "Content-Type": "application/json" },
  });
  check(res, { "predict 200": (r) => r.status === 200 });

  http.get("http://localhost:8003/");
  sleep(0.3);
}
