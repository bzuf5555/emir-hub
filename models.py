"""
MongoDB collection sxemalari (ma'lumotnoma uchun).

groups:
  marsit_id: str (unique)
  name: str
  telegram_chat_id: str | None
  is_active: bool

students:
  marsit_id: str (unique)
  name: str
  group_id: str  (groups.marsit_id)
  coin_balance: int
  is_active: bool

coin_transactions:
  student_marsit_id: str
  student_name: str
  amount: int
  reason: str
  created_at: datetime

check_logs:
  group_id: str  (groups.marsit_id)
  check_type: str  "morning" | "evening"
  results: list[{student_name, solved, coins}]
  solved_count: int
  unsolved_count: int
  checked_at: datetime
"""
