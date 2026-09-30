/** 입력 칸 아래에 서버가 알려준 항목별 에러를 보여준다. */
export default function FieldError({ errors, name }: { errors: Record<string, string>; name: string }) {
  return errors[name] ? <span className="field-error">{errors[name]}</span> : null;
}
