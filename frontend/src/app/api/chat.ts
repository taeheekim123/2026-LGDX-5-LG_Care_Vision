import {
  AVAILABLE_DATES,
  initialMessages,
  PROBLEM_OPTIONS,
  PRODUCTS,
  PRODUCT_TYPES,
  TIME_SLOTS,
} from "../data/mockChat";
import type { ChatContext, Message, ScheduleDateOption } from "../types/chat";

export function getInitialChatMessages(): Message[] {
  return initialMessages;
}

export function getProductCategories(): string[] {
  return PRODUCTS;
}

export function getProductTypes(productCategory: string): string[] {
  return PRODUCT_TYPES[productCategory] ?? [];
}

export function getAllProductTypes(): string[] {
  return Object.values(PRODUCT_TYPES).flat();
}

export function getProblemOptions(): string[] {
  return PROBLEM_OPTIONS;
}

export function getAvailableDates(): ScheduleDateOption[] {
  return AVAILABLE_DATES;
}

export function getTimeSlots(): string[] {
  return TIME_SLOTS;
}

export async function saveChatMessage(message: string, context: ChatContext): Promise<void> {
  void message;
  void context;
  // TODO: Replace with POST /api/chat-messages when backend is ready.
}

export async function requestAiChat(message: string, context: ChatContext): Promise<string> {
  void context;
  // TODO: Replace with POST /api/ai/chat when LLM backend is ready.
  return message;
}

