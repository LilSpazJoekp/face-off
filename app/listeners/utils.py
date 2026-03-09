class plural:  # noqa: N801
    """A class to format a number with a singular or plural form."""

    def __format__(self, format_spec: str) -> str:
        """Format the number with a singular or plural form."""
        v = self.value
        singular_form, _, plural_form = format_spec.partition("|")
        plural_form = plural_form or f"{singular_form}s"
        if abs(v) != 1:
            return f"{self.markdown_char}{v}{self.markdown_char} {plural_form}"
        return f"{self.markdown_char}{v}{self.markdown_char} {singular_form}"

    def __init__(self, value: int, markdown_char: str = "") -> None:
        """Initialize the class with a number."""
        self.value: int = value
        self.markdown_char: str = markdown_char
