import type { Message, ScheduleDateOption } from "../types/chat";

export const PRODUCTS = ["에어컨", "냉장고", "세탁기", "공기청정기"];

export const PRODUCT_TYPES: Record<string, string[]> = {
  "에어컨": ["스탠드형", "벽걸이형", "창문형"],
  "냉장고": ["일반형", "양문형", "김치냉장고"],
  "세탁기": ["드럼형", "통돌이형"],
  "공기청정기": ["스탠드형", "벽걸이형"],
};

export const PROBLEM_OPTIONS = [
  "전원이 불안정하거나 자주 꺼져요",
  "냉방/기능이 잘 작동하지 않아요",
  "필터에 먼지가 많이 쌓여 있어요",
  "소음이나 진동이 심해요",
  "그 외 다른 문제",
];

export const AVAILABLE_DATES: ScheduleDateOption[] = (() => {
  const dates: ScheduleDateOption[] = [];
  const today = new Date();
  for (let i = 1; i <= 7; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const days = ["일", "월", "화", "수", "목", "금", "토"];
    dates.push({
      label: `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]})`,
      value: d.toLocaleDateString("ko-KR"),
    });
  }
  return dates;
})();

export const TIME_SLOTS = ["09:00~11:00", "11:00~13:00", "14:00~16:00", "16:00~18:00"];

export const initialMessages: Message[] = [
  {
    id: "1",
    type: "bot",
    content: "안녕하세요!\nLG전자 온라인 채팅 서비스에 오신 것을 환영합니다.\n무엇을 도와드릴까요?",
    time: "오후 12:09",
    options: ["제품 문제 해결", "가전 관리 방법", "서비스 센터 연결"],
  },
];

