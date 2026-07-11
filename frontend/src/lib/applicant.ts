export type Applicant = Record<string, number>;

export function defaultApplicant(): Applicant {
  const a: Applicant = {
    limit_bal: 150000, sex: 2, education: 2, marriage: 1, age: 35,
    pay_0: 0, pay_2: 0, pay_3: 0, pay_4: 0, pay_5: 0, pay_6: 0,
  };
  for (let i = 1; i <= 6; i++) { a[`bill_amt${i}`] = 50000; a[`pay_amt${i}`] = 5000; }
  return a;
}
