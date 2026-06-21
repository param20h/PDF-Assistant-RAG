export const MIN_PASSWORD_LENGTH = 8;

export type PasswordRuleId =
  | "minLength"
  | "uppercase"
  | "lowercase"
  | "number"
  | "special"
  | "notCommon";

export type PasswordStrength = "weak" | "medium" | "strong";

export interface PasswordRuleResult {
  id: PasswordRuleId;
  passed: boolean;
}

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;/'`~]/;

const COMMON_PASSWORDS = new Set(
  [
    "123456",
    "1234567",
    "12345678",
    "123456789",
    "1234567890",
    "12345",
    "1234",
    "123123",
    "111111",
    "000000",
    "password",
    "password1",
    "password123",
    "passw0rd",
    "qwerty",
    "qwerty123",
    "qwertyuiop",
    "abc123",
    "admin",
    "admin123",
    "letmein",
    "welcome",
    "welcome1",
    "monkey",
    "dragon",
    "master",
    "login",
    "shadow",
    "sunshine",
    "princess",
    "football",
    "baseball",
    "iloveyou",
    "trustno1",
    "superman",
    "batman",
    "access",
    "hello",
    "charlie",
    "donald",
    "mustang",
    "696969",
    "654321",
    "987654321",
    "qazwsx",
    "asdfgh",
    "zxcvbnm",
    "1q2w3e4r",
    "1qaz2wsx",
    "aa123456",
    "p@ssw0rd",
    "changeme",
    "secret",
    "test123",
    "guest",
    "root",
    "toor",
  ].map((value) => value.toLowerCase())
);

function isCommonPassword(password: string): boolean {
  const normalized = password.trim().toLowerCase();
  return COMMON_PASSWORDS.has(normalized);
}

export function evaluatePasswordRules(password: string): PasswordRuleResult[] {
  return [
    { id: "minLength", passed: password.length >= MIN_PASSWORD_LENGTH },
    { id: "uppercase", passed: /[A-Z]/.test(password) },
    { id: "lowercase", passed: /[a-z]/.test(password) },
    { id: "number", passed: /\d/.test(password) },
    { id: "special", passed: SPECIAL_CHAR_REGEX.test(password) },
    { id: "notCommon", passed: password.length === 0 || !isCommonPassword(password) },
  ];
}

export function isPasswordValid(password: string): boolean {
  const rules = evaluatePasswordRules(password);
  return rules.every((rule) => rule.passed);
}

export function getPasswordStrength(password: string): PasswordStrength {
  if (!password) {
    return "weak";
  }

  const rules = evaluatePasswordRules(password);
  const coreRules = rules.filter((rule) => rule.id !== "notCommon");
  const passedCount = coreRules.filter((rule) => rule.passed).length;

  if (!rules.find((rule) => rule.id === "notCommon")?.passed) {
    return "weak";
  }

  if (passedCount <= 2) {
    return "weak";
  }

  if (passedCount <= 4) {
    return "medium";
  }

  if (password.length >= 12) {
    return "strong";
  }

  return "medium";
}

export function getPasswordStrengthProgress(strength: PasswordStrength): number {
  switch (strength) {
    case "weak":
      return 33;
    case "medium":
      return 66;
    case "strong":
      return 100;
  }
}

export function getPasswordStrengthColor(strength: PasswordStrength): string {
  switch (strength) {
    case "weak":
      return "bg-destructive";
    case "medium":
      return "bg-amber-500";
    case "strong":
      return "bg-emerald-500";
  }
}
