"use client";

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, CircleHelp, Eye, EyeOff, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Progress, ProgressIndicator, ProgressTrack } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  evaluatePasswordRules,
  getPasswordStrength,
  getPasswordStrengthColor,
  getPasswordStrengthProgress,
  type PasswordRuleId,
} from "@/lib/password-validation";

interface PasswordFieldProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  showRequirements?: boolean;
  showStrength?: boolean;
  autoComplete?: string;
  "aria-describedby"?: string;
  disabled?: boolean;
}

const RULE_LABEL_KEYS: Record<PasswordRuleId, string> = {
  minLength: "password.rules.minLength",
  uppercase: "password.rules.uppercase",
  lowercase: "password.rules.lowercase",
  number: "password.rules.number",
  special: "password.rules.special",
  notCommon: "password.rules.notCommon",
};

export function PasswordField({
  id,
  value,
  onChange,
  placeholder,
  showRequirements = true,
  showStrength = true,
  autoComplete = "new-password",
  "aria-describedby": ariaDescribedBy,
  disabled,
}: PasswordFieldProps) {
  const { t } = useTranslation();
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState(false);

  const rules = useMemo(() => evaluatePasswordRules(value), [value]);
  const strength = useMemo(() => getPasswordStrength(value), [value]);
  const strengthProgress = getPasswordStrengthProgress(strength);
  const strengthColor = getPasswordStrengthColor(strength);
  const checklistId = `${id}-requirements`;
  const strengthId = `${id}-strength`;

  const describedBy = [
    ariaDescribedBy,
    showRequirements ? checklistId : null,
    showStrength && value ? strengthId : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <label htmlFor={id} className="text-sm font-medium">
          {t("common.password")}
        </label>
        <Tooltip>
          <TooltipTrigger
            type="button"
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label={t("password.requirementsHelp")}
            disabled={disabled}
          >
            <CircleHelp className="w-3.5 h-3.5" />
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs text-left">
            <p className="font-medium mb-1">{t("password.requirementsTitle")}</p>
            <ul className="list-disc pl-4 space-y-0.5">
              {Object.values(RULE_LABEL_KEYS).map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="relative">
        <Input
          id={id}
          type={showPassword ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onBlur={() => setTouched(true)}
          required
          minLength={8}
          autoComplete={autoComplete}
          aria-describedby={describedBy || undefined}
          aria-invalid={touched && !rules.every((rule) => rule.passed) ? true : undefined}
          className="h-11 pr-10"
          disabled={disabled}
        />
        <button
          type="button"
          onClick={() => setShowPassword((current) => !current)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={showPassword ? t("password.hidePassword") : t("password.showPassword")}
          disabled={disabled}
        >
          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>

      {showStrength && value.length > 0 && (
        <div id={strengthId} className="space-y-1.5" aria-live="polite">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{t("password.strengthLabel")}</span>
            <span
              className={cn(
                "font-medium capitalize",
                strength === "weak" && "text-destructive",
                strength === "medium" && "text-amber-600 dark:text-amber-400",
                strength === "strong" && "text-emerald-600 dark:text-emerald-400"
              )}
            >
              {t(`password.strength.${strength}`)}
            </span>
          </div>
          <Progress value={strengthProgress} className="gap-0">
            <ProgressTrack className="h-1.5">
              <ProgressIndicator className={cn("transition-all", strengthColor)} />
            </ProgressTrack>
          </Progress>
        </div>
      )}

      {showRequirements && (value.length > 0 || touched) && (
        <ul
          id={checklistId}
          className="space-y-1 rounded-lg border border-border/60 bg-muted/30 p-3"
          aria-live="polite"
        >
          {rules.map((rule) => (
            <li
              key={rule.id}
              className={cn(
                "flex items-center gap-2 text-xs transition-colors",
                rule.passed ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
              )}
            >
              {rule.passed ? (
                <Check className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
              ) : (
                <X className="w-3.5 h-3.5 shrink-0 text-muted-foreground/70" aria-hidden="true" />
              )}
              <span>{t(RULE_LABEL_KEYS[rule.id])}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
