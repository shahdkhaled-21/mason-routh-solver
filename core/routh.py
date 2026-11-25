import re #use regular expressions to parse polynomial text
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

TOL = 1e-9  # tolerance for the real part of numerical roots


class RouthInputError(ValueError):
    """Raised when the polynomial text or coefficients are invalid."""

#function for formatting fractions 
#it returns the integer as-is if the denominator is 1 , otherwise, it returns the fraction in the form 'p/q (decimal)'
def fmt(x: Fraction) -> str:
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator} ({float(x):.4f})"

#function for formatting fractions in table cells
#it returns the integer as-is if the denominator is 1 , otherwise, it returns the fraction as a 4-decimal number
def fmt_cell(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{float(x):.4f}"

#function recieves the equation the user write and returns the coefficients of the polynomial in a list
def parse_polynomial(text:str) -> list:
    text = text.strip() #delete leading and trailing whitespace
    if not text: #if the text is empty raise an error
        raise RouthInputError("Enter a polynomial or a list of coefficients.")
    text = text.split("=")[0].replace(" ", "").replace("**", "^").replace("S", "s")
    # accept superscript powers as pasted from a PDF, e.g. s⁵ -> s^5
    text = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+",
                  lambda m: "^" + m.group().translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")),
                  text).replace("−", "-")
    try: #it checks if the text is a list of coefficients or a polynomial and returns the coefficients in a list
        if re.fullmatch(r"[-+0-9./,;]+", text): 
            coeffs = [Fraction(t) for t in re.split(r"[,;]", text) if t]
        else:
            coeffs = _parse_terms(text) 
    except (ValueError, ZeroDivisionError): #it raises an error if the text is not a valid polynomial or list of coefficients
        raise RouthInputError("Couldn't read the polynomial. Please Check the format.")
    if len(coeffs) < 2:
        raise RouthInputError("The polynomial needs degree 1 or higher.")
    if coeffs[0] == 0: #it raises an error if the first coefficient is zero because the polynomial is not valid
        raise RouthInputError("The first coefficient can't be zero.")
    if any(c == 0 for c in coeffs): #it raises an error if any coefficient is zero because the polynomial is not valid
        raise RouthInputError( 
            "Every power from s^0 to s^n must have a nonzero coefficient.")
    if not (all(c > 0 for c in coeffs) or all(c < 0 for c in coeffs)): #it raises an error if the coefficients are not all positive or all negative because the polynomial is not valid
        raise RouthInputError("All coefficients must have the same sign.")
    return coeffs


def _parse_terms(text: str) -> list:
    terms = re.findall(r"[+-]?[^+-]+", text) #splits the polynomial into terms based on the sign
    by_power = {} #to store the coefficients of each power of s
    for t in terms:
        m = re.fullmatch(r"([+-]?)([0-9./]*)\*?(?:s(?:\^(\d+))?)?", t) #it matches the term with the regex pattern and extracts the sign, coefficient, and power of s
        if not m or t in ("+", "-"):
            raise ValueError(t)
        sign, num, pw = m.groups()  #store the sign, coefficient, and power of s in variables
        has_s = "s" in t #check if the term has s in it
        if not has_s and not num: 
            raise ValueError(t)
        c = Fraction(num) if num else Fraction(1) #it converts the coefficient to a Fraction, if there is no coefficient it assumes it is 1
        if sign == "-": 
            c = -c
        p = (int(pw) if pw else 1) if has_s else 0 #it converts the power of s to an integer, if there is no power it assumes it is 1, if there is no s it assumes it is 0
        by_power[p] = by_power.get(p, 0) + c #it adds the coefficient to the corresponding power of s in the dictionary
    n = max(by_power)
    return [by_power.get(p, Fraction(0)) for p in range(n, -1, -1)]

#class to store the result of the Routh table calculation
@dataclass
class RouthResult:
    coeffs: list
    rows: list = field(default_factory=list)      # list of list[Fraction]
    labels: list = field(default_factory=list)    # 's^5', ..., 's^0'
    steps: list = field(default_factory=list)     # calculation strings
    first_column: list = field(default_factory=list)
    sign_changes: int = 0
    stable: bool = False
    special_case: str = ""                        # non-empty = special case hit


def build_routh_table(coeffs: list) -> RouthResult:
    """Build the full Routh table with a calculation string for every cell.

    cell[j] of the new row =
        (lower_row[0]*upper_row[j+1] - upper_row[0]*lower_row[j+1]) / lower_row[0]
    where lower_row is the row just above the new row (its first entry is
    the pivot) and upper_row is the row above lower_row.
    """
    n = len(coeffs) - 1 #degree of the polynomial
    width = n // 2 + 1 #number of columns in the Routh table 
    res = RouthResult(coeffs=list(coeffs)) 
    res.labels = [f"s^{n - i}" for i in range(n + 1)] #create labels for each row ex: s^5, s^4, s^3, s^2, s^1, s^0
    r_a = [coeffs[i] for i in range(0, n + 1, 2)] #create the first row of the Routh table with the coefficients of the even powers of s
    r_b = [coeffs[i] for i in range(1, n + 1, 2)] #create the second row of the Routh table with the coefficients of the odd powers of s
    pad = lambda r: r + [Fraction(0)] * (width - len(r)) #pad the rows with zeros to make them the same length as the width of the table
    res.rows = [pad(r_a), pad(r_b)] #store the first two rows in the result object
    res.steps.append(f"{res.labels[0]} row: coefficients {', '.join(fmt(c) for c in r_a)}")
    res.steps.append(f"{res.labels[1]} row: coefficients {', '.join(fmt(c) for c in r_b)}")
    
    #we start from the third row (k=2) and calculate each cell using the formula above, until we reach the last row (k=n)
    for k in range(2, n + 1):
        upper_row, lower_row = res.rows[k - 2], res.rows[k - 1]
        if lower_row[0] == 0:
            if all(v == 0 for v in lower_row):
                res.special_case = (f"All-zero row at {res.labels[k-1]}: "
                                    "special case.")
            else:
                res.special_case = (f"Zero in first column at {res.labels[k-1]}: "
                                    "special case .")
            break
        row = []
        for j in range(width):
            upper_next = upper_row[j + 1] if j + 1 < width else Fraction(0) #get the next value in the upper row, if it is out of bounds, set it to 0
            lower_next = lower_row[j + 1] if j + 1 < width else Fraction(0) #get the next value in the lower row, if it is out of bounds, set it to 0
            val = (lower_row[0] * upper_next - upper_row[0] * lower_next) / lower_row[0] #calculate the value of the cell using the formula 
            row.append(val)
            if upper_next == 0 and lower_next == 0:   # padding column, nothing to show
                continue
            res.steps.append( #show the calculation for each cell in the Routh table
                f"{res.labels[k]}, col {j+1}: "
                f"({fmt_cell(lower_row[0])}×{fmt_cell(upper_next)} − "
                f"{fmt_cell(upper_row[0])}×{fmt_cell(lower_next)}) / "
                f"{fmt_cell(lower_row[0])} = {fmt_cell(val)}")
        res.rows.append(row)
    #check for special cases after building the table, if any special case was hit, we add it to the steps and return the result
    if res.special_case:
        res.steps.append(res.special_case)
        return res
    
    if all(v == 0 for v in res.rows[-1]): #check if the last row is all zeros, if it is, we add a special case to the steps and return the result
        res.special_case = "All-zero row: special case."
        res.steps.append(res.special_case)
        return res

    res.first_column = [r[0] for r in res.rows] #get the first column of the Routh table, which is used to determine the stability of the system
    if any(v == 0 for v in res.first_column): #check if there is a zero in the first column, if there is, we add a special case to the steps and return the result
        res.special_case = "Zero in first column: special case."
        res.steps.append(res.special_case)
        return res
    
    sign = lambda v: 1 if v > 0 else -1 #function to determine the sign of a value, returns 1 for positive values and -1 for negative values
    res.sign_changes = sum(
        1 for i in range(len(res.first_column) - 1)
        if sign(res.first_column[i]) != sign(res.first_column[i + 1])) #count the number of sign changes in the first column, which is used to determine the number of roots in the right half plane
    res.stable = res.sign_changes == 0 #if there are no sign changes in the first column, the system is stable, otherwise it is unstable
    return res

#function to calculate the roots of the polynomial using numpy.roots
#it returns a dictionary with the roots, the roots in the right half plane (RHP), the count of RHP roots, and the tolerance used for determining RHP roots
def numeric_roots(coeffs: list, tol: float = TOL) -> dict:
    roots = np.roots([float(c) for c in coeffs])
    rhp = [r for r in roots if r.real > tol] #get the roots in the right half plane (RHP) by checking if the real part of the root is greater than the tolerance
    return {"roots": list(roots), "rhp": rhp, "rhp_count": len(rhp), "tol": tol}

#function collects all the functions above and returns the Routh table, the roots of the polynomial, and a boolean indicating if the number of RHP roots matches the number of sign changes in the first column of the Routh table
def analyze(text: str) -> tuple:
    coeffs = parse_polynomial(text)
    res = build_routh_table(coeffs)
    if res.special_case:
        return res, None, None
    rt = numeric_roots(coeffs)
    return res, rt, rt["rhp_count"] == res.sign_changes