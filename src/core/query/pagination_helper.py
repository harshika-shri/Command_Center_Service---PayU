from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PaginationMetadata:
    total_records: int
    total_pages: int
    current_page: int
    page_size: int


class PaginationHelper:
    @staticmethod
    def total_pages(
        total_records: int,
        page_size: int,
    ) -> int:
        if total_records <= 0:
            return 0

        return (total_records + page_size - 1) // page_size

    @staticmethod
    def build_metadata(
        *,
        total_records: int,
        current_page: int,
        page_size: int,
    ) -> PaginationMetadata:
        return PaginationMetadata(
            total_records=total_records,
            total_pages=PaginationHelper.total_pages(
                total_records,
                page_size,
            ),
            current_page=current_page,
            page_size=page_size,
        )
