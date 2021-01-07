from autoplan.labels import Labels


class GeneralRainfallLabels(Labels):
    CleanFirst = 0
    CleanInSC = 1
    SingleLoop = 2

    @classmethod
    def from_string(cls, s):
        if hasattr(cls, s):
            return getattr(cls, s)
        else:
            raise Exception(f"Unknown label {s}")


class DetailedRainfallLabels(Labels):
    TNFirst = 0
    CleanInSC = 1
    AccumStyle = 2
    SumFirst = 3
    CountFirst = 4
    NegFirst = 5
    SentinelFirst = 6
    NoCleaning = 7
    CleanUpAfter = 8
    FarOff = 9
    Rec = 10

    @classmethod
    def from_string(cls, s):
        if hasattr(cls, s):
            return getattr(cls, s)
        elif s == 'T&NFirst':
            return cls.TNFirst
        elif s == 'CleanInS&C':
            return cls.CleanInSC
        else:
            raise Exception(f"Unknown label {s}")


class CountWhere(Labels):
    Helper = 0
    Rainfall = 1
    Own = 2
    Multiple = 3

    @classmethod
    def from_string(cls, s):
        if s == 'own':
            return cls.Own
        elif s == 'helper':
            return cls.Helper
        elif s == 'rainfall':
            return cls.Rainfall
        elif s == 'multiple':
            return cls.Multiple
        else:
            raise Exception(f"Unknown label {s}")
