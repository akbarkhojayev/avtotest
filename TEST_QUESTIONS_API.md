# Test Questions API - Pagination

## Endpoint: `/api/tests/questions/`

Savollarni 20 talik qilib paginatsiya bilan olish.

### Request

```bash
GET /api/tests/questions/?page=1&page_size=20
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Sahifa raqami |
| `page_size` | integer | 20 | Bir sahifada nechta savol (max: 100) |
| `category` | integer | - | Kategoriya ID bo'yicha filtrlash |

### Response Format

```json
{
  "count": 1179,
  "next": "http://localhost:8000/api/tests/questions/?page=2&page_size=20",
  "previous": null,
  "results": [
    {
      "id": 1,
      "question_text": "Savol matni...",
      "photo": null,
      "difficulty": "medium",
      "category": null,
      "answers": [
        {
          "id": 1,
          "answer_text": "Javob 1",
          "is_correct": false,
          "order": 1
        },
        {
          "id": 2,
          "answer_text": "Javob 2",
          "is_correct": true,
          "order": 2
        }
      ]
    },
    ...
  ]
}
```

## Example Requests

### 1. Birinchi 20 ta savol olish
```bash
curl -X GET "http://localhost:8000/api/tests/questions/?page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. 2-sahifadagi savollar
```bash
curl -X GET "http://localhost:8000/api/tests/questions/?page=2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Bir sahifada 10 ta savol
```bash
curl -X GET "http://localhost:8000/api/tests/questions/?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Kategoriya bo'yicha filter qilish
```bash
curl -X GET "http://localhost:8000/api/tests/questions/?category=1&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Jami savollar soni (1179 ta) |
| `next` | string \| null | Keyingi sahifaning URL'i |
| `previous` | string \| null | Oldingi sahifaning URL'i |
| `results` | array | Savollar massivi |

## Pagination Details

- **Default page size:** 20
- **Maximum page size:** 100
- **Total questions:** 1,179
- **Total pages:** 59 (20 ta sahifa) yoki 12 (100 ta sahifa)

## Authentication

Barcha so'rovlar `Authorization: Bearer TOKEN` header bilan yuborilingan bo'lishi kerak.
