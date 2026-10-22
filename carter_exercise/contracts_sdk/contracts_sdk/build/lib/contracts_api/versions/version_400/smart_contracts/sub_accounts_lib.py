from abc import abstractmethod, ABC
from datetime import datetime

from ..common.docs import _common_docs_path
from ....utils import symbols, types_utils




class VaultFunctionsABC(ABC):
    # Sub-Account Vault Attributes.
    sub_account_id: str
    sub_account_type: str

    # Sub-Account Vault Methods.
    

    @abstractmethod
    def get_sub_account_activation_datetime(self) -> datetime:
        pass

    @classmethod
    def _spec(cls, language_code=symbols.Languages.ENGLISH) -> types_utils.ClassSpec:
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_methods = [
            types_utils.MethodSpec(
                name="get_sub_account_activation_datetime",
                docstring="""
                    Returns the Sub-Account's activation datetime.
                """,
                return_value=types_utils.ReturnValueSpec(
                    docstring=f"""
                        The Sub-Account's activation datetime, constructed from the
                        `activation_timestamp` of the
                        [CreateAccountRequest](api/core_api#_core_api_v2_accounts_Account_CreateAccount).
                        It is equivalent to the `effective_datetime` of the Smart Contract's
                        [ActivationHookArguments]({_common_docs_path}classes/#ActivationHookArguments)
                        and can be set in the past if the account opening is backdated. This is
                        a timezone-aware UTC datetime using the
                        [ZoneInfo]({_common_docs_path}native_objects#ZoneInfo) class.
                    """,
                    type="datetime",
                ),
            ),
        ]
        

        public_methods.sort(key=lambda x: x.name)

        return types_utils.ClassSpec(
            name="VaultFunctions",
            docstring="This object contains information about a Sub-Account.",
            public_attributes=[
                types_utils.ValueSpec(
                    name="sub_account_id",
                    type="str",
                    docstring="The ID of the Sub-Account.",
                ),
                types_utils.ValueSpec(
                    name="sub_account_type",
                    type="str",
                    docstring="The type of the Sub-Account.",
                ),
            ],
            public_methods=public_methods,
        )
