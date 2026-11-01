"""SOLO PARA PRUEBAS: genera un crudo sintético con el MISMO esquema (50 columnas)
y el mismo formato de IDS_mapping.csv que el dataset real, para validar el
pipeline sin acceso a Drive. Nunca usar estas cifras en un informe.

    python tests/generar_sintetico.py --n 6000 --destino /tmp/crudo
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MEDS = ["metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride", "acetohexamide",
        "glipizide", "glyburide", "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose", "miglitol",
        "troglitazone", "tolazamide", "examide", "citoglipton", "insulin", "glyburide-metformin",
        "glipizide-metformin", "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone"]

MAPPING = """admission_type_id,description
1,Emergency
2,Urgent
3,Elective
4,Newborn
5,Not Available
6,NULL
7,Trauma Center
8,Not Mapped
,
discharge_disposition_id,description
1,Discharged to home
2,Discharged/transferred to another short term hospital
3,Discharged/transferred to SNF
4,Discharged/transferred to ICF
5,Discharged/transferred to another type of inpatient care institution
6,Discharged/transferred to home with home health service
7,Left AMA
8,Discharged/transferred to home under care of Home IV provider
9,Admitted as an inpatient to this hospital
10,Neonate discharged to another hospital for neonatal aftercare
11,Expired
12,Still patient or expected to return for outpatient services
13,Hospice / home
14,Hospice / medical facility
15,Discharged/transferred within this institution to Medicare approved swing bed
16,Discharged/transferred/referred another institution for outpatient services
17,Discharged/transferred/referred to this institution for outpatient services
18,NULL
19,"Expired at home. Medicaid only, hospice."
20,"Expired in a medical facility. Medicaid only, hospice."
21,"Expired, place unknown. Medicaid only, hospice."
22,Discharged/transferred to another rehab fac including rehab units of a hospital .
23,Discharged/transferred to a long term care hospital.
24,Discharged/transferred to a nursing facility certified under Medicaid but not certified under Medicare.
25,Not Mapped
26,Unknown/Invalid
27,Discharged/transferred to a federal health care facility.
28,Discharged/transferred/referred to a psychiatric hospital of psychiatric distinct part unit of a hospital
29,Discharged/transferred to a Critical Access Hospital (CAH).
30,Discharged/transferred/referred to another institution for outpatient services
,
admission_source_id,description
1, Physician Referral
2,Clinic Referral
3,HMO Referral
4,Transfer from a hospital
5, Transfer from a Skilled Nursing Facility (SNF)
6, Transfer from another health care facility
7, Emergency Room
8, Court/Law Enforcement
9, Not Available
10, Transfer from critial access hospital
11,Normal Delivery
12, Premature Delivery
13, Sick Baby
14, Extramural Birth
15,Not Available
17,NULL
18, Transfer From Another Home Health Agency
19,Readmission to Same Home Health Agency
20, Not Mapped
21,Unknown/Invalid
22, Transfer from hospital inpt/same fac reslt in a sep claim
23, Born inside this hospital
24, Born outside this hospital
25, Transfer from Ambulatory Surgery Center
26,Transfer from Hospice
"""


def generar(n: int, semilla: int = 0) -> pd.DataFrame:
    r = np.random.default_rng(semilla)
    n_pac = int(n * 0.7)
    pac = r.integers(1, n_pac, n) * 9 + 135
    inpatient = r.poisson(0.64, n)
    edad_idx = r.choice(10, n, p=[.002, .007, .016, .037, .095, .17, .22, .256, .17, .027])
    disp = r.choice([1, 3, 6, 18, 2, 22, 11, 5, 25, 4, 7, 23, 13, 14, 19],
                    n, p=[.59, .14, .127, .036, .02, .02, .016, .012, .01, .008, .006, .004, .003, .003, .005])
    logit = -2.6 + 0.35 * inpatient + 0.03 * (edad_idx - 6) + 0.3 * (disp == 3) + r.normal(0, .6, n)
    p30 = 1 / (1 + np.exp(-logit))
    u = r.random(n)
    readm = np.where(u < p30, "<30", np.where(u < p30 + 0.35, ">30", "NO"))
    readm[disp == 11] = "NO"

    def cat(vals, probs, miss=0.0):
        s = r.choice(vals, n, p=probs).astype(object)
        s[r.random(n) < miss] = None
        return s

    icd = np.array(["428", "250.83", "276", "414", "786", "486", "682", "V27", "E888", "715",
                    "599", "250", "250.6", "038", "434", "996", "585", "402", "780", "571"])
    df = pd.DataFrame({
        "encounter_id": np.arange(n) * 7 + 12522,
        "patient_nbr": pac,
        "race": cat(["Caucasian", "AfricanAmerican", "Hispanic", "Other", "Asian"], [.76, .19, .02, .015, .015], .022),
        "gender": cat(["Female", "Male", "Unknown/Invalid"], [.5378, .4621, .0001]),
        "age": np.array([f"[{10*i}-{10*(i+1)})" for i in range(10)])[edad_idx],
        "weight": cat(["[75-100)", "[50-75)", "[100-125)"], [.5, .3, .2], .968),
        "admission_type_id": r.choice([1, 2, 3, 5, 6, 8, 7], n, p=[.53, .18, .19, .047, .05, .002, .001]),
        "discharge_disposition_id": disp,
        "admission_source_id": r.choice([7, 1, 17, 4, 6, 2, 5, 9, 20], n, p=[.565, .29, .067, .031, .022, .011, .008, .003, .003]),
        "time_in_hospital": r.integers(1, 15, n),
        "payer_code": cat(["MC", "HM", "SP", "BC", "MD", "CP"], [.53, .1, .08, .08, .06, .15], .396),
        "medical_specialty": cat(["InternalMedicine", "Emergency/Trauma", "Family/GeneralPractice", "Cardiology",
                                  "Surgery-General", "Nephrology", "Orthopedics", "Radiologist", "Pulmonology",
                                  "Psychiatry", "Urology", "ObstetricsandGynecology"],
                                 [.28, .15, .14, .1, .06, .03, .03, .02, .02, .02, .03, .12], .49),
        "num_lab_procedures": np.clip(r.normal(43, 19.7, n).round(), 1, 132).astype(int),
        "num_procedures": r.integers(0, 7, n),
        "num_medications": np.clip(r.normal(16, 8, n).round(), 1, 81).astype(int),
        "number_outpatient": r.poisson(0.37, n),
        "number_emergency": r.poisson(0.2, n),
        "number_inpatient": inpatient,
        "diag_1": cat(icd, None, .0002),
        "diag_2": cat(icd, None, .0035),
        "diag_3": cat(icd, None, .014),
        "number_diagnoses": r.integers(1, 17, n),
        "max_glu_serum": cat([">200", ">300", "Norm"], [.3, .25, .45], .947),
        "A1Cresult": cat([">7", ">8", "Norm"], [.22, .48, .3], .833),
    })
    for m in MEDS:
        if m in ("examide", "citoglipton"):
            df[m] = "No"
        elif m in ("metformin", "insulin", "glipizide", "glyburide"):
            df[m] = r.choice(["No", "Steady", "Up", "Down"], n, p=[.6, .3, .05, .05])
        else:
            df[m] = r.choice(["No", "Steady"], n, p=[.97, .03])
    df["change"] = r.choice(["No", "Ch"], n, p=[.54, .46])
    df["diabetesMed"] = r.choice(["Yes", "No"], n, p=[.77, .23])
    df["readmitted"] = readm
    assert df.shape[1] == 50
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--destino", default="datos/crudo")
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args()
    d = Path(a.destino)
    d.mkdir(parents=True, exist_ok=True)
    generar(a.n, a.semilla).to_parquet(d / "diabetic_data.parquet", index=False)
    (d / "IDS_mapping.csv").write_text(MAPPING, encoding="utf-8")
    print(f"sintético {a.n} filas -> {d}")


if __name__ == "__main__":
    main()
