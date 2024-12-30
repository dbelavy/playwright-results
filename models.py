from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class SharedState:
    QScript_code: Optional[str] = None
    PRODA_code: Optional[str] = None
    FourCyte_code: Optional[str] = None  # Changed from 4Cyte_code to be a valid Python identifier
    paused: bool = True
    exit: bool = False
    credentials_file: str = "credentials.json"

@dataclass
class PatientDetails:
    family_name: str
    given_name: Optional[str] = None
    dob: Optional[str] = None
    medicare_number: Optional[str] = None
    sex: Optional[str] = None

    def __post_init__(self):
        # Validate DOB format if provided
        if self.dob:
            try:
                datetime.strptime(self.dob, "%d%m%Y")
            except ValueError:
                raise ValueError("DOB must be in DDMMYYYY format")
        
        # Validate sex if provided
        if self.sex and self.sex not in ["M", "F", "I"]:
            raise ValueError("Sex must be 'M', 'F', or 'I'")

    @classmethod
    def from_args(cls, args, required_fields: list[str]):
        """Create PatientDetails from argparse args and required fields"""
        details = {}
        
        # Handle each field based on args or user input
        details['family_name'] = args.family_name if args.family_name else (
            input("Enter Family Name: ") if 'family_name' in required_fields else None)
        
        details['given_name'] = args.given_name if args.given_name else (
            input("Enter Given Name: ") if 'given_name' in required_fields else None)
        
        if 'dob' in required_fields:
            if args.dob:
                details['dob'] = args.dob
            else:
                while True:
                    dob_input = input("Enter DOB (DDMMYYYY): ")
                    try:
                        datetime.strptime(dob_input, "%d%m%Y")
                        details['dob'] = dob_input
                        break
                    except ValueError:
                        print("Invalid date. Please enter a valid date in DDMMYYYY format.")
        
        details['medicare_number'] = str(args.medicare_number) if args.medicare_number else (
            str(input("Enter Medicare Number: ")) if 'medicare_number' in required_fields else None)
        
        if 'sex' in required_fields:
            details['sex'] = args.sex.upper() if args.sex else None
            while not details['sex'] or details['sex'] not in ["M", "F", "I"]:
                details['sex'] = input("Enter Sex (M, F, or I): ").upper()
        
        return cls(**details)

    def to_cli_args(self) -> str:
        """Convert patient details to CLI arguments string"""
        flags = []
        if self.family_name:
            flags.append(f"--family_name {self.family_name}")
        if self.given_name:
            flags.append(f"--given_name {self.given_name}")
        if self.dob:
            flags.append(f"--dob {self.dob}")
        if self.medicare_number:
            flags.append(f"--medicare_number {self.medicare_number}")
        if self.sex:
            flags.append(f"--sex {self.sex}")
        return " ".join(flags)
