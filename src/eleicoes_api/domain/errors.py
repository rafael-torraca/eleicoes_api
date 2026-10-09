class ElectionError(Exception):
    """Erro base relacionado a consultas eleitorais."""


class CandidateNotFoundError(ElectionError):
    """Candidato não encontrado na eleição consultada."""


class ElectionDataUnavailableError(ElectionError):
    """Dados eleitorais indisponíveis."""


class ElectionResourceNotFoundError(ElectionDataUnavailableError):
    """Arquivo ou recurso eleitoral não encontrado na fonte de dados."""