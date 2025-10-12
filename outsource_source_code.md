# Outsource Document: Add Processing Time to Kindle Push History

## 1. Goal

Add processing time reporting to the "Book pushed to Kindle successfully" message in the webUI History section. The processing time should be displayed in the history details dialog when users click the information button for a successful Kindle push event.

## 2. Complete Folder Structure

```
komga/
├── komga/src/main/kotlin/org/gotson/komga/domain/model/HistoricalEvent.kt
├── komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt
└── komga_custom/
    └── push_to_kindle.py

komga-webui/
└── src/views/HistoryView.vue
```

## 3. Source Code (per file)

### File: komga/src/main/kotlin/org/gotson/komga/domain/model/HistoricalEvent.kt

The `BookPushedToKindleSuccess` class needs to be updated to include processing time in its properties.


```kotlin
package org.gotson.komga.domain.model

import com.github.f4b6a3.tsid.TsidCreator
import java.nio.file.Path
import java.time.LocalDateTime

sealed class HistoricalEvent(
  val type: String,
  val bookId: String? = null,
  val seriesId: String? = null,
  val properties: Map<String, String> = emptyMap(),
  val timestamp: LocalDateTime = LocalDateTime.now(),
  val id: String = TsidCreator.getTsid256().toString(),
) {
  class BookFileDeleted(
    book: Book,
    reason: String,
  ) : HistoricalEvent(
      type = "BookFileDeleted",
      bookId = book.id,
      seriesId = book.seriesId,
      properties =
        mapOf(
          "reason" to reason,
          "name" to book.path.toString(),
        ),
    )

  class SeriesFolderDeleted(
    seriesId: String,
    seriesPath: Path,
    reason: String,
  ) : HistoricalEvent(
      type = "SeriesFolderDeleted",
      seriesId = seriesId,
      properties =
        mapOf(
          "reason" to reason,
          "name" to seriesPath.toString(),
        ),
    ) {
    constructor(series: Series, reason: String) : this(series.id, series.path, reason)
  }

  class BookConverted(
    book: Book,
    previous: Book,
  ) : HistoricalEvent(
      type = "BookConverted",
      bookId = book.id,
      seriesId = book.seriesId,
      properties =
        mapOf(
          "name" to book.path.toString(),
          "former file" to previous.path.toString(),
        ),
    )

  class BookImported(
    book: Book,
    series: Series,
    source: Path,
    upgrade: Boolean,
  ) : HistoricalEvent(
      type = "BookImported",
      bookId = book.id,
      seriesId = series.id,
      properties =
        mapOf(
          "name" to book.path.toString(),
          "source" to source.toString(),
          "upgrade" to if (upgrade) "Yes" else "No",
        ),
    )

  class DuplicatePageDeleted(
    book: Book,
    page: BookPageNumbered,
  ) : HistoricalEvent(
      type = "DuplicatePageDeleted",
      bookId = book.id,
      seriesId = book.seriesId,
      properties =
        mapOf(
          "name" to book.path.toString(),
          "page number" to page.pageNumber.toString(),
          "page file name" to page.fileName,
          "page file hash" to page.fileHash,
          "page file size" to page.fileSize.toString(),
          "page media type" to page.mediaType,
        ),
    )

  class BookPushedToKindleInitialized(
    book: Book,
    series: Series,
  ) : HistoricalEvent(
    type = "BookPushedToKindleInitialized",
    bookId = book.id,
    seriesId = series.id,
    properties =
      mapOf(
        "name" to book.path.toString(),
        "series" to series.name,
      ),
  )

  class BookPushedToKindleSuccess(
    book: Book,
    series: Series,
    kindlePath: String,
  ) : HistoricalEvent(
    type = "BookPushedToKindleSuccess",
    bookId = book.id,
    seriesId = series.id,
    properties =
      mapOf(
        "name" to book.path.toString(),
        "series" to series.name,
        "kindle_path" to kindlePath,
      ),
  )

  class BookPushedToKindleFailed(
    book: Book,
    series: Series,
    error: String,
  ) : HistoricalEvent(
    type = "BookPushedToKindleFailed",
    bookId = book.id,
    seriesId = series.id,
    properties =
      mapOf(
        "name" to book.path.toString(),
        "series" to series.name,
        "error" to error,
      ),
  )
}

```
### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt

The `pushToKindle` method needs to be updated to:
1. Capture processing time from the Python script output
2. Include processing time in the `BookPushedToKindleSuccess` historical event


```kotlin
package org.gotson.komga.interfaces.api.rest

import io.github.oshai.kotlinlogging.KotlinLogging
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.Parameter
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import jakarta.servlet.http.HttpServletRequest
import jakarta.validation.Valid
import org.gotson.komga.application.tasks.HIGHEST_PRIORITY
import org.gotson.komga.application.tasks.HIGH_PRIORITY
import org.gotson.komga.application.tasks.LOWEST_PRIORITY
import org.gotson.komga.application.tasks.TaskEmitter
import org.gotson.komga.domain.model.BookSearch
import org.gotson.komga.domain.model.Dimension
import org.gotson.komga.domain.model.DomainEvent
import org.gotson.komga.domain.model.HistoricalEvent
import org.gotson.komga.domain.model.ImageConversionException
import org.gotson.komga.domain.model.MarkSelectedPreference
import org.gotson.komga.domain.model.Media
import org.gotson.komga.domain.model.MediaExtensionEpub
import org.gotson.komga.domain.model.MediaNotReadyException
import org.gotson.komga.domain.model.MediaProfile
import org.gotson.komga.domain.model.ReadStatus
import org.gotson.komga.domain.model.SearchCondition
import org.gotson.komga.domain.model.SearchContext
import org.gotson.komga.domain.model.SearchOperator
import org.gotson.komga.domain.model.ThumbnailBook
import org.gotson.komga.domain.persistence.BookMetadataRepository
import org.gotson.komga.domain.persistence.BookRepository
import org.gotson.komga.domain.persistence.HistoricalEventRepository
import org.gotson.komga.domain.persistence.MediaRepository
import org.gotson.komga.domain.persistence.ReadListRepository
import org.gotson.komga.domain.persistence.SeriesRepository
import org.gotson.komga.domain.persistence.ThumbnailBookRepository
import org.gotson.komga.domain.service.BookAnalyzer
import org.gotson.komga.domain.service.BookLifecycle
import org.gotson.komga.infrastructure.image.ImageAnalyzer
import org.gotson.komga.infrastructure.jooq.UnpagedSorted
import org.gotson.komga.infrastructure.mediacontainer.ContentDetector
import org.gotson.komga.infrastructure.openapi.OpenApiConfiguration
import org.gotson.komga.infrastructure.openapi.PageableAsQueryParam
import org.gotson.komga.infrastructure.openapi.PageableWithoutSortAsQueryParam
import org.gotson.komga.infrastructure.security.KomgaPrincipal
import org.gotson.komga.infrastructure.web.getMediaTypeOrDefault
import org.gotson.komga.interfaces.api.CommonBookController
import org.gotson.komga.interfaces.api.ContentRestrictionChecker
import org.gotson.komga.interfaces.api.WebPubGenerator
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_DIVINA_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_POSITION_LIST_JSON
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_POSITION_LIST_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_WEBPUB_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.WPPublicationDto
import org.gotson.komga.interfaces.api.getBookLastModified
import org.gotson.komga.interfaces.api.persistence.BookDtoRepository
import org.gotson.komga.interfaces.api.rest.dto.BookDto
import org.gotson.komga.interfaces.api.rest.dto.BookImportBatchDto
import org.gotson.komga.interfaces.api.rest.dto.BookMetadataUpdateDto
import org.gotson.komga.interfaces.api.rest.dto.PageDto
import org.gotson.komga.interfaces.api.rest.dto.R2Positions
import org.gotson.komga.interfaces.api.rest.dto.ReadListDto
import org.gotson.komga.interfaces.api.rest.dto.ReadProgressUpdateDto
import org.gotson.komga.interfaces.api.rest.dto.ThumbnailBookDto
import org.gotson.komga.interfaces.api.rest.dto.patch
import org.gotson.komga.interfaces.api.rest.dto.restrictUrl
import org.gotson.komga.interfaces.api.rest.dto.toDto
import org.gotson.komga.interfaces.api.setNotModified
import org.springframework.context.ApplicationEventPublisher
import org.springframework.data.domain.Page
import org.springframework.data.domain.PageRequest
import org.springframework.data.domain.Pageable
import org.springframework.data.domain.Sort
import org.springframework.format.annotation.DateTimeFormat
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.security.core.annotation.AuthenticationPrincipal
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PatchMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.context.request.ServletWebRequest
import org.springframework.web.context.request.WebRequest
import org.springframework.web.multipart.MultipartFile
import org.springframework.web.server.ResponseStatusException
import java.lang.ProcessBuilder
import java.nio.file.NoSuchFileException
import java.time.LocalDate
import java.time.ZoneOffset

private val logger = KotlinLogging.logger {}

@RestController
@RequestMapping(produces = [MediaType.APPLICATION_JSON_VALUE])
class BookController(
  private val taskEmitter: TaskEmitter,
  private val bookAnalyzer: BookAnalyzer,
  private val bookLifecycle: BookLifecycle,
  private val bookRepository: BookRepository,
  private val bookMetadataRepository: BookMetadataRepository,
  private val historicalEventRepository: HistoricalEventRepository,
  private val mediaRepository: MediaRepository,
  private val bookDtoRepository: BookDtoRepository,
  private val readListRepository: ReadListRepository,
  private val seriesRepository: SeriesRepository,
  private val contentDetector: ContentDetector,
  private val imageAnalyzer: ImageAnalyzer,
  private val eventPublisher: ApplicationEventPublisher,
  private val thumbnailBookRepository: ThumbnailBookRepository,
  private val webPubGenerator: WebPubGenerator,
  private val contentRestrictionChecker: ContentRestrictionChecker,
  private val commonBookController: CommonBookController,
) {
  @Deprecated("use /v1/books/list instead")
  @PageableAsQueryParam
  @GetMapping("api/v1/books")
  @Operation(summary = "List books", description = "Use POST /api/v1/books/list instead. Deprecated since 1.19.0.", tags = [OpenApiConfiguration.TagNames.BOOKS, OpenApiConfiguration.TagNames.DEPRECATED])
  fun getAllBooksDeprecated(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "search", required = false) searchTerm: String? = null,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @RequestParam(name = "media_status", required = false) mediaStatus: List<Media.Status>? = null,
    @RequestParam(name = "read_status", required = false) readStatus: List<ReadStatus>? = null,
    @RequestParam(name = "released_after", required = false)
    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
    releasedAfter: LocalDate? = null,
    @RequestParam(name = "tag", required = false) tags: List<String>? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !searchTerm.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    val bookSearch =
      BookSearch(
        SearchCondition.AllOfBook(
          buildList {
            if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfBook(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
            if (!mediaStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(mediaStatus.map { SearchCondition.MediaStatus(SearchOperator.Is(it)) }))
            if (!readStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(readStatus.map { SearchCondition.ReadStatus(SearchOperator.Is(it)) }))
            if (!tags.isNullOrEmpty()) add(SearchCondition.AnyOfBook(tags.map { SearchCondition.Tag(SearchOperator.Is(it)) }))
            releasedAfter?.let { add(SearchCondition.ReleaseDate(SearchOperator.After(it.atStartOfDay(ZoneOffset.UTC)))) }
          },
        ),
        searchTerm,
      )

    return bookDtoRepository
      .findAll(bookSearch, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @PageableAsQueryParam
  @PostMapping("api/v1/books/list")
  @Operation(summary = "List books", tags = [OpenApiConfiguration.TagNames.BOOKS])
  fun getBooks(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestBody search: BookSearch,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !search.fullTextSearch.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository
      .findAll(search, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List latest books", description = "Return newly added or updated books.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableWithoutSortAsQueryParam
  @GetMapping("api/v1/books/latest")
  fun getBooksLatest(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort = Sort.by(Sort.Order.desc("lastModifiedDate"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository
      .findAll(
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List books on deck", description = "Return first unread book of series with at least one book read and no books in progress.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableWithoutSortAsQueryParam
  @GetMapping("api/v1/books/ondeck")
  fun getBooksOnDeck(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> =
    bookDtoRepository
      .findAllOnDeck(
        principal.user.id,
        principal.user.getAuthorizedLibraryIds(libraryIds),
        page,
        principal.user.restrictions,
      ).map { it.restrictUrl(!principal.user.isAdmin) }

  @Operation(summary = "List duplicate books", description = "Return books that have the same file hash.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableAsQueryParam
  @GetMapping("api/v1/books/duplicates")
  @PreAuthorize("hasRole('ADMIN')")
  fun getBooksDuplicates(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        else -> Sort.by(Sort.Order.asc("fileHash"))
      }

    val pageRequest =
      if (unpaged)
        Pageable.unpaged()
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository.findAllDuplicates(principal.user.id, pageRequest)
  }

  @Operation(summary = "Get book details", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}")
  fun getBookById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto =
    bookDtoRepository.findByIdOrNull(bookId, principal.user.id)?.let {
      contentRestrictionChecker.checkContentRestriction(principal.user, it)

      it.restrictUrl(!principal.user.isAdmin)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get previous book in series", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/previous")
  fun getBookSiblingPrevious(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookDtoRepository
      .findPreviousInSeriesOrNull(bookId, principal.user.id)
      ?.restrictUrl(!principal.user.isAdmin)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Get next book in series", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/next")
  fun getBookSiblingNext(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookDtoRepository
      .findNextInSeriesOrNull(bookId, principal.user.id)
      ?.restrictUrl(!principal.user.isAdmin)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book's readlists", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/readlists")
  fun getReadListsByBookId(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
  ): List<ReadListDto> {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return readListRepository
      .findAllContainingBookId(bookId, principal.user.getAuthorizedLibraryIds(null), principal.user.restrictions)
      .map { it.toDto() }
  }

  @Operation(summary = "Get book's poster image", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/thumbnail"],
    produces = [MediaType.IMAGE_JPEG_VALUE],
  )
  fun getBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ByteArray {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookLifecycle.getThumbnailBytes(bookId)?.bytes ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Get book poster image", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(value = ["api/v1/books/{bookId}/thumbnails/{thumbnailId}"], produces = [MediaType.IMAGE_JPEG_VALUE])
  fun getBookThumbnailById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ): ByteArray {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookLifecycle.getThumbnailBytesByThumbnailId(thumbnailId)?.bytes
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book posters", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @GetMapping(value = ["api/v1/books/{bookId}/thumbnails"], produces = [MediaType.APPLICATION_JSON_VALUE])
  fun getBookThumbnails(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
  ): Collection<ThumbnailBookDto> {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return thumbnailBookRepository
      .findAllByBookId(bookId)
      .map { it.toDto() }
  }

  @Operation(summary = "Add book poster", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PostMapping(value = ["api/v1/books/{bookId}/thumbnails"], consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
  @PreAuthorize("hasRole('ADMIN')")
  fun addUserUploadedBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @RequestParam("file") file: MultipartFile,
    @RequestParam("selected") selected: Boolean = true,
  ): ThumbnailBookDto {
    val book = bookRepository.findByIdOrNull(bookId) ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

    val mediaType = file.inputStream.buffered().use { contentDetector.detectMediaType(it) }
    if (!contentDetector.isImage(mediaType))
      throw ResponseStatusException(HttpStatus.UNSUPPORTED_MEDIA_TYPE)

    return bookLifecycle
      .addThumbnailForBook(
        ThumbnailBook(
          bookId = book.id,
          thumbnail = file.bytes,
          type = ThumbnailBook.Type.USER_UPLOADED,
          selected = selected,
          fileSize = file.bytes.size.toLong(),
          mediaType = mediaType,
          dimension = imageAnalyzer.getDimension(file.inputStream.buffered()) ?: Dimension(0, 0),
        ),
        if (selected) MarkSelectedPreference.YES else MarkSelectedPreference.NO,
      ).toDto()
  }

  @Operation(summary = "Mark book poster as selected", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PutMapping("api/v1/books/{bookId}/thumbnails/{thumbnailId}/selected")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun markBookThumbnailSelected(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    thumbnailBookRepository.findByIdOrNull(thumbnailId)?.let {
      thumbnailBookRepository.markSelected(it)
      eventPublisher.publishEvent(DomainEvent.ThumbnailBookAdded(it.copy(selected = true)))
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Delete book poster", description = "Only uploaded posters can be deleted.", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @DeleteMapping("api/v1/books/{bookId}/thumbnails/{thumbnailId}")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteUserUploadedBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    thumbnailBookRepository.findByIdOrNull(thumbnailId)?.let {
      try {
        bookLifecycle.deleteThumbnailForBook(it)
      } catch (e: IllegalArgumentException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, e.message)
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book pages", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @GetMapping("api/v1/books/{bookId}/pages")
  fun getBookPages(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): List<PageDto> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val media = mediaRepository.findById(book.id)
      when (media.status) {
        Media.Status.UNKNOWN -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book has not been analyzed yet")
        Media.Status.OUTDATED -> throw ResponseStatusException(
          HttpStatus.NOT_FOUND,
          "Book is outdated and must be re-analyzed",
        )

        Media.Status.ERROR -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book analysis failed")
        Media.Status.UNSUPPORTED -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book format is not supported")
        Media.Status.READY -> {
          val pages = if (media.profile == MediaProfile.PDF) bookAnalyzer.getPdfPagesDynamic(media) else media.pages
          pages.mapIndexed { index, bookPage ->
            PageDto(
              number = index + 1,
              fileName = bookPage.fileName,
              mediaType = bookPage.mediaType,
              width = bookPage.dimension?.width,
              height = bookPage.dimension?.height,
              sizeBytes = bookPage.fileSize,
            )
          }
        }
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book page image", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @ApiResponse(content = [Content(mediaType = "image/*", schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/pages/{pageNumber}"],
    produces = [MediaType.ALL_VALUE],
  )
  @PreAuthorize("hasRole('PAGE_STREAMING')")
  fun getBookPageByNumber(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    request: ServletWebRequest,
    @PathVariable bookId: String,
    @PathVariable pageNumber: Int,
    @Parameter(
      description = "Convert the image to the provided format.",
      schema = Schema(allowableValues = ["jpeg", "png"]),
    )
    @RequestParam(value = "convert", required = false)
    convertTo: String?,
    @Parameter(description = "If set to true, pages will start at index 0. If set to false, pages will start at index 1.")
    @RequestParam(value = "zero_based", defaultValue = "false")
    zeroBasedIndex: Boolean,
    @Parameter(description = "Some very limited server driven content negotiation is handled. If a book is a PDF book, and the Accept header contains 'application/pdf' as a more specific type than other 'image/' types, a raw PDF page will be returned.")
    @RequestHeader(HttpHeaders.ACCEPT, required = false)
    acceptHeaders: MutableList<MediaType>?,
    @RequestParam(value = "contentNegotiation", defaultValue = "true")
    contentNegotiation: Boolean,
  ): ResponseEntity<ByteArray> = commonBookController.getBookPageInternal(bookId, if (zeroBasedIndex) pageNumber + 1 else pageNumber, convertTo, request, principal, if (contentNegotiation) acceptHeaders else null)

  @Operation(summary = "Get book page thumbnail", description = "The image is resized to 300px on the largest dimension.", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/pages/{pageNumber}/thumbnail"],
    produces = [MediaType.IMAGE_JPEG_VALUE],
  )
  fun getBookPageThumbnailByNumber(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    request: WebRequest,
    @PathVariable bookId: String,
    @PathVariable pageNumber: Int,
  ): ResponseEntity<ByteArray> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      val media = mediaRepository.findById(bookId)
      if (request.checkNotModified(getBookLastModified(media))) {
        return@let ResponseEntity
          .status(HttpStatus.NOT_MODIFIED)
          .setNotModified(media)
          .body(ByteArray(0))
      }

      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      try {
        val pageContent = bookLifecycle.getBookPage(book, pageNumber, resizeTo = 300)

        ResponseEntity
          .ok()
          .contentType(getMediaTypeOrDefault(pageContent.mediaType))
          .setNotModified(media)
          .body(pageContent.bytes)
      } catch (ex: IndexOutOfBoundsException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, "Page number does not exist")
      } catch (ex: ImageConversionException) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, ex.message)
      } catch (ex: MediaNotReadyException) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book analysis failed")
      } catch (ex: NoSuchFileException) {
        logger.warn(ex) { "File not found: $book" }
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "File not found, it may have moved")
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book's WebPub manifest", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE, MEDIATYPE_DIVINA_JSON_VALUE],
  )
  fun getBookWebPubManifest(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ResponseEntity<WPPublicationDto> {
    val manifest = commonBookController.getWebPubManifestInternal(principal, bookId, webPubGenerator)
    return ResponseEntity
      .ok()
      .contentType(manifest.mediaType)
      .body(manifest)
  }

  @Operation(summary = "List book's positions", description = "The Positions API is a proposed standard for OPDS 2 and Readium. It is used by the Epub Reader.", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/positions"],
    produces = [MEDIATYPE_POSITION_LIST_JSON_VALUE],
  )
  fun getBookPositions(
    request: HttpServletRequest,
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ResponseEntity<R2Positions> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      val media = mediaRepository.findById(book.id)

      if (ServletWebRequest(request).checkNotModified(getBookLastModified(media))) {
        return ResponseEntity
          .status(HttpStatus.NOT_MODIFIED)
          .setNotModified(media)
          .body(null)
      }

      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val extension =
        mediaRepository.findExtensionByIdOrNull(book.id) as? MediaExtensionEpub
          ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

      ResponseEntity
        .ok()
        .contentType(MEDIATYPE_POSITION_LIST_JSON)
        .setNotModified(media)
        .body(R2Positions(extension.positions.size, extension.positions))
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book's WebPub manifest (Epub)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/epub"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE],
  )
  fun getBookWebPubManifestEpub(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestEpubInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Get book's WebPub manifest (PDF)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/pdf"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE],
  )
  fun getBookWebPubManifestPdf(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestPdfInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Get book's WebPub manifest (DiViNa)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/divina"],
    produces = [MEDIATYPE_DIVINA_JSON_VALUE],
  )
  fun getBookWebPubManifestDivina(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestDivinaInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Analyze book", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PostMapping("api/v1/books/{bookId}/analyze")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun bookAnalyze(
    @PathVariable bookId: String,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      taskEmitter.analyzeBook(book, HIGH_PRIORITY)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Refresh book metadata", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PostMapping("api/v1/books/{bookId}/metadata/refresh")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun bookRefreshMetadata(
    @PathVariable bookId: String,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      taskEmitter.refreshBookMetadata(book, priority = HIGH_PRIORITY)
      taskEmitter.refreshBookLocalArtwork(book, priority = HIGH_PRIORITY)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Update book metadata", description = "Set a field to null to unset the metadata. You can omit fields you don't want to update.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/{bookId}/metadata")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateBookMetadata(
    @PathVariable bookId: String,
    @Parameter(description = "Metadata fields to update. Set a field to null to unset the metadata. You can omit fields you don't want to update.")
    @Valid
    @RequestBody
    newMetadata: BookMetadataUpdateDto,
  ) = bookMetadataRepository.findByIdOrNull(bookId)?.let { existing ->
    val updated = existing.patch(newMetadata)
    bookMetadataRepository.update(updated)

    bookRepository.findByIdOrNull(bookId)?.let { updatedBook ->
      taskEmitter.aggregateSeriesMetadata(updatedBook.seriesId)
      updatedBook.let { eventPublisher.publishEvent(DomainEvent.BookUpdated(it)) }
    }
  } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Update book metadata in bulk", description = "Set a field to null to unset the metadata. You can omit fields you don't want to update.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/metadata")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateBookMetadataByBatch(
    @Parameter(description = "A map of book IDs which values are the metadata fields to update. Set a field to null to unset the metadata. You can omit fields you don't want to update.")
    @Valid
    @RequestBody
    newMetadatas: Map<String, BookMetadataUpdateDto>,
  ) {
    val updatedBooks =
      newMetadatas.mapNotNull { (bookId, newMetadata) ->
        bookMetadataRepository.findByIdOrNull(bookId)?.let { existing ->
          val updated = existing.patch(newMetadata)
          bookMetadataRepository.update(updated)

          bookRepository.findByIdOrNull(bookId)
        }
      }

    updatedBooks.forEach { eventPublisher.publishEvent(DomainEvent.BookUpdated(it)) }
    updatedBooks.map { it.seriesId }.distinct().forEach { taskEmitter.aggregateSeriesMetadata(it) }
  }

  @Operation(summary = "Mark book's read progress", description = "Mark book as read and/or change page progress.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/{bookId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun markBookReadProgress(
    @PathVariable bookId: String,
    @Parameter(description = "page can be omitted if completed is set to true. completed can be omitted, and will be set accordingly depending on the page passed and the total number of pages in the book.")
    @Valid
    @RequestBody
    readProgress: ReadProgressUpdateDto,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      try {
        if (readProgress.completed != null && readProgress.completed)
          bookLifecycle.markReadProgressCompleted(book.id, principal.user)
        else
          bookLifecycle.markReadProgress(book, principal.user, readProgress.page!!)
      } catch (e: IllegalArgumentException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, e.message)
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Mark book as unread", description = "Mark book as unread", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @DeleteMapping("api/v1/books/{bookId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun deleteBookReadProgress(
    @PathVariable bookId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      bookLifecycle.deleteReadProgress(book, principal.user)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Import books", tags = [OpenApiConfiguration.TagNames.BOOK_IMPORT])
  @PostMapping("api/v1/books/import")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun importBooks(
    @RequestBody bookImportBatch: BookImportBatchDto,
  ) {
    bookImportBatch.books.forEach {
      try {
        taskEmitter.importBook(
          sourceFile = it.sourceFile,
          seriesId = it.seriesId,
          copyMode = bookImportBatch.copyMode,
          destinationName = it.destinationName,
          upgradeBookId = it.upgradeBookId,
          priority = HIGHEST_PRIORITY,
        )
      } catch (e: Exception) {
        logger.error(e) { "Error while creating import task for: $it" }
      }
    }
  }

  @Operation(summary = "Delete book file", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @DeleteMapping("api/v1/books/{bookId}/file")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteBookFile(
    @PathVariable bookId: String,
  ) {
    taskEmitter.deleteBook(
      bookId = bookId,
      priority = HIGHEST_PRIORITY,
    )
  }

  @Operation(summary = "Regenerate books posters", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PutMapping("api/v1/books/thumbnails")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun booksRegenerateThumbnails(
    @RequestParam(name = "for_bigger_result_only", required = false) forBiggerResultOnly: Boolean = false,
  ) {
    taskEmitter.findBookThumbnailsToRegenerate(forBiggerResultOnly, LOWEST_PRIORITY)
  }

  @PostMapping("api/v1/books/{bookId}/push-to-kindle")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun pushToKindle(
    @PathVariable bookId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    // Immediate feedback when the button is pressed
    logger.info { "[push_to_kindle] Upload requested from WebUI for book: $bookId. Starting..." }

    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val media = mediaRepository.findById(book.id)
      if (media.status != Media.Status.READY) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book is not ready")
      }

      // Create initialization event
      val series = book.seriesId?.let { seriesRepository.findByIdOrNull(it) }
      if (series != null) {
        historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleInitialized(book, series))
        logger.info { "[push_to_kindle] Created initialization event for book: $bookId" }
      } else {
        logger.warn { "[push_to_kindle] Could not find series for book: $bookId, skipping initialization event" }
      }

      try {
        val processBuilder = ProcessBuilder("python3", "/app/komga_custom/push_to_kindle.py", book.url.path)
        processBuilder.redirectErrorStream(true)
        val process = processBuilder.start()
        val reader = process.inputStream.bufferedReader()
        val preface = "[push_to_kindle] Upload requested from WebUI for book: $bookId. Starting...\n"
        val output = reader.readText()
        logger.info { "Push to kindle script output: $preface$output" }
        val exitCode = process.waitFor()
        
        if (exitCode == 0) {
          // Parse Kindle path from output
          val kindlePath = extractKindlePathFromOutput(output)
          if (kindlePath != null) {
            // Create success event for successful push
            if (series != null) {
              historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleSuccess(book, series, kindlePath))
            } else {
              logger.warn { "[push_to_kindle] Could not find series for book: $bookId, skipping success event" }
            }
            logger.info { "[push_to_kindle] Successfully created success event for book: $bookId, Kindle path: $kindlePath" }
          } else {
            logger.warn { "[push_to_kindle] Push succeeded but could not extract Kindle path from output for book: $bookId" }
            // Create success event even without kindle path
            if (series != null) {
              historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleSuccess(book, series, ""))
            }
          }
        } else {
          // Script failed - parse error from output
          val errorMessage = extractErrorFromOutput(output) ?: "Script failed with exit code: $exitCode"
          logger.error { "[push_to_kindle] Script failed for book: $bookId, exit code: $exitCode, error: $errorMessage" }
          // Create failure event
          if (series != null) {
            historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleFailed(book, series, errorMessage))
          }
          throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Push to kindle script failed: $errorMessage")
        }
      } catch (e: Exception) {
        logger.error(e) { "Error while executing push to kindle script for book: $bookId" }
        // Create failure event
        val errorMessage = e.message ?: "Script execution failed: ${e::class.simpleName}"
        if (series != null) {
          historicalEventRepository.insert(HistoricalEvent.BookPushedToKindleFailed(book, series, errorMessage))
        }
        throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error while executing push to kindle script: $errorMessage")
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  private fun extractKindlePathFromOutput(output: String): String? {
    // Extract the target folder from the output
    // Look for structured output pattern: HISTORICAL_EVENT_KINDLE_PATH:folder_name
    val lines = output.split("\n")
    for (line in lines) {
      if (line.startsWith("HISTORICAL_EVENT_KINDLE_PATH:")) {
        return line.substringAfter("HISTORICAL_EVENT_KINDLE_PATH:").trim()
      }
      // Fallback to old patterns for backward compatibility
      if (line.contains("Successfully uploaded") && line.contains("to Kindle folder:")) {
        val match = Regex("Successfully uploaded .* to Kindle folder: (.*)").find(line)
        if (match != null) {
          return match.groupValues[1].trim()
        }
      }
      if (line.contains("Multiple files detected, using series folder:")) {
        val match = Regex("Multiple files detected, using series folder: (.*)").find(line)
        if (match != null) {
          return match.groupValues[1].trim()
        }
      }
    }
    return null
  }

  private fun extractErrorFromOutput(output: String): String? {
    // Extract error information from the output
    val lines = output.split("\n")
    for (line in lines) {
      if (line.startsWith("SCRIPT_ERROR_MESSAGE:")) {
        return line.substringAfter("SCRIPT_ERROR_MESSAGE:").trim()
      }
      if (line.startsWith("KCC_ERROR_MESSAGE:")) {
        return line.substringAfter("KCC_ERROR_MESSAGE:").trim()
      }
      if (line.startsWith("FILE_ERROR_MESSAGE:")) {
        return line.substringAfter("FILE_ERROR_MESSAGE:").trim()
      }
    }
    return null
  }
}

```
### File: komga_custom/push_to_kindle.py

The `main()` function needs to be updated to:
1. Add timing measurement around the main processing logic
2. Output processing time in a structured format for the backend to parse


```python
import os
import sys
import tempfile
import zipfile
import subprocess
import io
import urllib.parse
import shlex
from PIL import Image
from typing import List
from pathlib import Path
from clean_cbz import clean_cbz

# NOTE: You need to install the following python packages:
# pip install Pillow

# --- Kindle configuration from environment variables ---
KINDLE_IP = os.environ.get("KINDLE_IP", "192.168.29.55")
KINDLE_USER = os.environ.get("KINDLE_USER", "root") 
KINDLE_REMOTE_PATH = os.environ.get("KINDLE_REMOTE_PATH" ,"/mnt/us/book")
KINDLE_SSH_PASSWORD = os.environ.get("KINDLE_SSH_PASSWORD", "dummy")  # Empty for passwordless auth
KINDLE_SSH_PORT = os.environ.get("KINDLE_SSH_PORT", "2222")

# Validate required environment variables
if not KINDLE_IP:
    print("Warning: KINDLE_IP not set, using default value. Please set KINDLE_IP environment variable.")
if not KINDLE_USER:
    print("Warning: KINDLE_USER not set, using default value. Please set KINDLE_USER environment variable.")
if not KINDLE_REMOTE_PATH:
    print("Warning: KINDLE_REMOTE_PATH not set, using default value. Please set KINDLE_REMOTE_PATH environment variable.")
if not KINDLE_SSH_PASSWORD:
    print("Info: KINDLE_SSH_PASSWORD not set, using passwordless SSH authentication.")
else:
    print("Info: Using password-based SSH authentication.")

def decode_url_path(url_path: str) -> str:
    """
    Decode URL-encoded path to actual file system path.
    """
    try:
        # Decode URL-encoded characters
        decoded_path = urllib.parse.unquote(url_path)
        return decoded_path
    except Exception as e:
        print(f"Error decoding URL path {url_path}: {e}")
        return url_path

def get_files_list_from_webui() -> List[str]:
    """
    This function gets the file list from the command line arguments.
    The Komga backend will call this script with the file paths of the book/series.
    """
    if len(sys.argv) < 2:
        print("Usage: python push_to_kindle.py <file1> <file2> ...")
        sys.exit(1)
    
    # Decode URL-encoded paths
    decoded_paths = [decode_url_path(path) for path in sys.argv[1:]]
    return decoded_paths




def extract_series_name_from_path(file_path: str) -> str:
    """
    Extract series name from file path by looking for directory structure.
    Assumes structure: /path/to/library/SeriesName/VolumeName/file.cbz
    """
    try:
        # Check if the path has the expected structure
        if not file_path:
            return None
            
        # Normalize the path
        normalized_path = os.path.normpath(file_path)
        
        # Split the path
        parts = normalized_path.split(os.sep)
        
        # Check if we have at least 2 parts (series folder and file)
        if len(parts) < 2:
            return None
            
        # Get the directory containing the file (second to last part)
        series_name = parts[-2]
        
        # Check if series name is empty or just dots
        if not series_name or series_name == '.' or series_name == '..':
            return None
        
        # Clean up series name for Kindle folder
        # Remove special characters, limit length
        clean_name = ''.join(c for c in series_name if c.isalnum() or c in ' -_').strip()
        return clean_name[:100] if clean_name else None  # Increased to 100 characters for full series names
    except Exception:
        return None

def is_epub_file(file_path: str) -> bool:
    """
    Check if the file is an EPUB format.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if file is EPUB, False otherwise
    """
    if not file_path:
        return False
    
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext == '.epub' or file_ext == '.pdf'

def push_to_kindle(file_path: str, target_folder: str = None, original_filename: str = None):
    """
    Pushes a file to Kindle using scp with configurable authentication and folder organization.
    Preserves original filename during SCP transfer.
    """
    print("[push_to_kindle] Received command to push file to Kindle.", flush=True)
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    print(f"--- Debug: Pushing to Kindle ---")
    print(f"File path: {file_path}")
    print(f"Target folder: {target_folder}")
    print(f"Original filename: {original_filename}")

    try:
        # Use original filename if provided, otherwise use current filename
        filename = original_filename if original_filename else os.path.basename(file_path)
        
        # Determine remote path based on target folder and check if we need special handling
        use_shell = False
        if target_folder and target_folder.strip():
            # Check if target folder has spaces or non-ASCII characters
            if ' ' in target_folder or any(ord(c) > 127 for c in target_folder):
                # Use shell command with proper quoting for special characters
                remote_path = f"{KINDLE_USER}@{KINDLE_IP}:\"{KINDLE_REMOTE_PATH}/{target_folder}/\""
                use_shell = True
            else:
                remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/{target_folder}/"
        else:
            remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/New/"
        
        # Build the scp command based on authentication method and whether we need shell
        if use_shell:
            # Use shell execution for paths with special characters
            if KINDLE_SSH_PASSWORD:
                command_str = f"sshpass -p {KINDLE_SSH_PASSWORD} scp -P {KINDLE_SSH_PORT} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \"{file_path}\" {remote_path}\"{filename}\""
            else:
                command_str = f"scp -P {KINDLE_SSH_PORT} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \"{file_path}\" {remote_path}\"{filename}\""
            
            print(f"Executing shell command: {command_str}")
            result = subprocess.run(command_str, shell=True, capture_output=True, text=True, timeout=300)
        else:
            # Use normal subprocess list for simple paths
            if KINDLE_SSH_PASSWORD:
                command = [
                    "sshpass",
                    "-p", KINDLE_SSH_PASSWORD,
                    "scp",
                    "-P", KINDLE_SSH_PORT,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    file_path,
                    f"{remote_path}{filename}"
                ]
            else:
                command = [
                    "scp",
                    "-P", KINDLE_SSH_PORT,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    file_path,
                    f"{remote_path}{filename}"
                ]
            
            print(f"Executing command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            folder_display = target_folder if target_folder else "New"
            print(f"Successfully uploaded {filename} to Kindle folder: {folder_display}")
            # Add structured output for better parsing by backend
            print(f"HISTORICAL_EVENT_KINDLE_PATH:{folder_display}")
            if result.stdout.strip():
                print(f"Stdout: {result.stdout}")
        else:
            print(f"Error uploading file to Kindle.")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            if result.stdout:
                print(f"Stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print(f"Upload timed out after 300 seconds")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print(f"--- End Debug ---")
        # Remove the temporary file after upload if it exists and is in /tmp
        try:
            if file_path.startswith("/tmp/") and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed temporary file: {file_path}")
        except Exception as cleanup_err:
            print(f"Warning: Failed to remove temporary file {file_path}: {cleanup_err}")


def check_kindle_connectivity() -> bool:
    """
    Check if the Kindle device is reachable via SSH.
    
    Returns:
        bool: True if Kindle is reachable, False otherwise
    """
    print(f"Checking connectivity to Kindle at {KINDLE_IP}:{KINDLE_SSH_PORT}...")
    
    try:
        # Build a simple SSH command to test connectivity
        if KINDLE_SSH_PASSWORD:
            # Password-based authentication
            command = [
                "sshpass",
                "-p", KINDLE_SSH_PASSWORD,
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                f"{KINDLE_USER}@{KINDLE_IP}",
                "echo 'connection_test'"
            ]
        else:
            # Passwordless authentication (using SSH keys)
            command = [
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                f"{KINDLE_USER}@{KINDLE_IP}",
                "echo 'connection_test'"
            ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✓ Kindle connectivity check passed")
            return True
        else:
            print("✗ Kindle connectivity check failed")
            if result.stderr:
                print(f"Connection error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Kindle connectivity check timed out")
        return False
    except Exception as e:
        print(f"✗ Kindle connectivity check error: {e}")
        return False

def create_remote_folder(folder_name: str) -> bool:
    """
    Create a remote folder on Kindle device.
    Checks connectivity first and terminates if Kindle is unreachable.
    
    Args:
        folder_name: Name of the folder to create
        
    Returns:
        bool: True if folder was created successfully, False otherwise
    """
    # First check if Kindle is reachable
    if not check_kindle_connectivity():
        print("❌ ERROR: Cannot reach Kindle device. Terminating push operation.")
        print(f"Please check that:")
        print(f"  - Kindle IP ({KINDLE_IP}) is correct")
        print(f"  - Kindle SSH port ({KINDLE_SSH_PORT}) is correct") 
        print(f"  - Kindle is connected to the network")
        print(f"  - SSH credentials are correct")
        sys.exit(1)  # Terminate the entire script
    
    print(f"Creating folder on Kindle: {folder_name}")
    
    try:
        remote_path = f"{KINDLE_USER}@{KINDLE_IP}:{KINDLE_REMOTE_PATH}/{folder_name}"
        
        # For SSH command, escape folder name properly 
        # Check if folder name has spaces or special characters
        if ' ' in folder_name or any(ord(c) > 127 for c in folder_name):
            # Use shell command with proper quoting for special characters
            mkdir_command = f"mkdir -p \"{KINDLE_REMOTE_PATH}/{folder_name}\""
        else:
            mkdir_command = f"mkdir -p {KINDLE_REMOTE_PATH}/{folder_name}"
        
        # Build the ssh command to create directory
        if KINDLE_SSH_PASSWORD:
            # Password-based authentication
            command = [
                "sshpass",
                "-p", KINDLE_SSH_PASSWORD,
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"{KINDLE_USER}@{KINDLE_IP}",
                mkdir_command
            ]
        else:
            # Passwordless authentication (using SSH keys)
            command = [
                "ssh",
                "-p", KINDLE_SSH_PORT,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"{KINDLE_USER}@{KINDLE_IP}",
                mkdir_command
            ]
        
        print(f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✓ Successfully created folder: {folder_name}")
            if result.stdout.strip():
                print(f"Stdout: {result.stdout}")
            return True
        else:
            print(f"✗ Error creating folder on Kindle.")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            if result.stdout:
                print(f"Stdout: {result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ SSH command timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"✗ An error occurred while creating folder: {e}")
        return False

def process_with_kcc(book_path: str, output_path: str) -> tuple[bool, str, str]:
    """
    Process a comic file using Kindle Comic Converter (KCC).
    Always applies watermark removal before KCC processing.
    
    Args:
        book_path: Path to the comic file (CBZ/CBR)
        output_path: Directory where processed file should be saved
        
    Returns:
        tuple: (success_status, output_file_path, original_filename)
    """
    kcc_script_dir = os.path.dirname(os.path.abspath(__file__))
    kcc_script = os.path.join(kcc_script_dir, "kcc-c2e.py")
    
    if not os.path.exists(kcc_script):
        print(f"Error: KCC script not found at {kcc_script}")
        # Fallback for Docker environment
        kcc_script = "/app/komga_custom/kcc-c2e.py"
        if not os.path.exists(kcc_script):
            print(f"Error: KCC script not found at {kcc_script} either.")
            return False
    
    # Always clean the CBZ first (watermark removal)
    print("Applying watermark removal before KCC processing...")
    cleaned_cbz_path = clean_cbz(book_path)
    if not cleaned_cbz_path or not os.path.exists(cleaned_cbz_path):
        print("CBZ cleaning failed, using original file")
        cleaned_cbz_path = book_path
    else:
        print(f"CBZ cleaned successfully: {cleaned_cbz_path}")
    
    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(book_path))[0]
    # Create full output path with specific filename
    output_file_path = os.path.join(output_path, f"{base_filename}_kcc.cbz")
    
    print(f"Processing with KCC: {cleaned_cbz_path}")
    print(f"Output file: {output_file_path}")
    
    try:
        # Add PYTHONPATH to include the directory containing kindlecomicconverter module
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(kcc_script)
        command = [
            "python3",
            "-c",
            f"import sys; sys.path.insert(0, '{os.path.dirname(kcc_script)}'); exec(open('{kcc_script}').read())",
            "-p", "KPW5",
#            "-q",
#            "-u",
            "-m",
            "--cp", "2",
            "--mozjpeg",
            "-f", "CBZ",
            "-o", output_file_path,
            cleaned_cbz_path  # Use cleaned CBZ
        ]
        print(f"Executing KCC command with PYTHONPATH={env['PYTHONPATH']}")
        print(f"Command: {' '.join(command)}")
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            print("KCC processing completed successfully")
            if result.stdout.strip():
                print(f"KCC stdout: {result.stdout}")
            return True, output_file_path, os.path.basename(book_path)
        else:
            print("Error during KCC processing")
            print(f"Return code: {result.returncode}")
            if result.stderr:
                print(f"KCC stderr: {result.stderr}")
            if result.stdout:
                print(f"KCC stdout: {result.stdout}")
            return False, cleaned_cbz_path, os.path.basename(book_path)
    except subprocess.TimeoutExpired:
        print("KCC processing timed out after 600 seconds")
        return False, cleaned_cbz_path, os.path.basename(book_path)
    except Exception as e:
        print(f"Error during KCC processing: {e}")
        return False, cleaned_cbz_path, os.path.basename(book_path)

def main():
    """
    Main function to process and push files to Kindle with folder organization.
    """
    print("SCRIPT_STATUS:STARTING")
    file_paths = get_files_list_from_webui()
    print(f"Processing files: {file_paths}")

    # Determine target folder based on number of files
    target_folder = "New"
    if len(file_paths) > 1:
        # For multiple files, try to extract series name from first file
        series_name = extract_series_name_from_path(file_paths[0])
        if series_name:
            target_folder = series_name
            print(f"Multiple files detected, using series folder: {target_folder}")
        else:
            print("Multiple files detected but couldn't determine series, using 'New' folder")
    else:
        print("Single file detected, using 'New' folder")

    # Create the target folder on Kindle
    print("SCRIPT_STATUS:CREATING_FOLDER")
    folder_success = create_remote_folder(target_folder)
    if not folder_success:
        print("SCRIPT_STATUS:FAILED")
        print("SCRIPT_ERROR_CODE:FOLDER_CREATION_FAILED")
        print("SCRIPT_ERROR_MESSAGE:Failed to create folder on Kindle device")
        sys.exit(1)

    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    all_success = True
    for file_path in file_paths:
        print(f"--- Processing file: {file_path} ---")
        print(f"FILE_STATUS:PROCESSING")
        print(f"FILE_PATH:{file_path}")

        # Check if file is EPUB
        if is_epub_file(file_path):
            print(f"EPUB file detected, skipping KCC processing and pushing directly.")
            kcc_output_file = file_path
            kcc_success = True
            cleaned_cbz_path = False
            original_filename = os.path.basename(file_path)
        else:
            kcc_output_dir = temp_dir

            kcc_success, cleaned_cbz_path, original_filename = process_with_kcc(file_path, kcc_output_dir)
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            kcc_output_file = os.path.join(kcc_output_dir, f"{base_filename}_kcc.cbz")

        if kcc_success:
            if os.path.exists(kcc_output_file):
                print(f"KCC processing successful. Pushing file to Kindle.")
                print(f"FILE_STATUS:KCC_SUCCESS")
                push_to_kindle(kcc_output_file, target_folder, original_filename)
            else:
                print(f"Error: KCC reported success, but output file '{kcc_output_file}' not found.")
                print(f"FILE_STATUS:FAILED")
                print(f"FILE_ERROR_CODE:OUTPUT_FILE_NOT_FOUND")
                print(f"FILE_ERROR_MESSAGE:KCC reported success, but output file not found")
                all_success = False
        else:
            print(f"KCC processing failed for {file_path}. The file will not be pushed to Kindle.")
            print(f"FILE_STATUS:FAILED")
            print(f"FILE_ERROR_CODE:KCC_PROCESSING_FAILED")
            print(f"FILE_ERROR_MESSAGE:KCC processing failed")
            all_success = False

        # Remove cleaned CBZ if it was created
        if cleaned_cbz_path and os.path.exists(cleaned_cbz_path):
            try:
                os.remove(cleaned_cbz_path)
                print(f"Removed cleaned CBZ: {cleaned_cbz_path}")
            except Exception as cleanup_err:
                print(f"Warning: Failed to remove cleaned CBZ {cleaned_cbz_path}: {cleanup_err}")

        print(f"--- Finished processing file: {file_path} ---")

    if all_success:
        print("SCRIPT_STATUS:SUCCESS")
    else:
        print("SCRIPT_STATUS:FAILED")
        print("SCRIPT_ERROR_CODE:ONE_OR_MORE_FILES_FAILED")
        print("SCRIPT_ERROR_MESSAGE:One or more files failed to process")
        # Exit with non-zero code to ensure Kotlin controllers detect the failure
        sys.exit(1)


if __name__ == "__main__":
    main()

```
### File: komga-webui/src/views/HistoryView.vue

The `formatPropertyKey` and `showDetails` methods may need updates to properly display the processing time in the history details dialog.

## 4. Data Structures


```vue
<template>
  <v-container fluid class="pa-6">
    <v-data-table
      :headers="headers"
      :items="items"
      :options.sync="options"
      :server-items-length="totalElements"
      :loading="loading"
      sort-by="timestamp"
      :sort-desc="true"
      multi-sort
      class="elevation-1"
      :footer-props="{
        itemsPerPageOptions: [20, 50, 100]
      }"
    >
      <template v-slot:item.type="{ item }">
        <v-icon
          :title="$t(`enums.historical_event_type.${item.type}`)"
          :color="getEventColor(item.type)"
        >{{ getIcon(item.type) }}</v-icon>
      </template>

      <template v-slot:item.seriesId="{ item }">
        <router-link v-if="getSeries(item.seriesId)"
                     :to="{name: 'browse-series', params: {seriesId: item.seriesId}}"
                     class="link-underline"
        >{{ getSeries(item.seriesId).metadata.title }}
        </router-link>
        <template v-else>{{ item.seriesId }}</template>
      </template>

      <template v-slot:item.bookId="{ item }">
        <router-link v-if="getBook(item.bookId)"
                     :to="{name: 'browse-book', params: {bookId: item.bookId}}"
                     class="link-underline"
        >{{ getBook(item.bookId).metadata.title }}
        </router-link>
        <template v-else>{{ item.bookId }}</template>
      </template>

      <template v-slot:item.timestamp="{ item }">
        {{
          new Intl.DateTimeFormat($i18n.locale, {
            dateStyle: 'medium',
            timeStyle: 'short'
          }).format(item.timestamp)
        }}
      </template>

      <template v-slot:item.properties="{ item }">
        <v-btn icon small @click="showDetails(item)">
          <v-icon small>mdi-information</v-icon>
        </v-btn>
      </template>

      <template v-slot:footer.prepend>
        <v-btn icon @click="loadData">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </template>

    </v-data-table>

    <v-dialog
      v-model="dialogDetails"
      scrollable
    >
      <v-card v-if="dialogDetailsItem">
        <v-card-title>{{ $t(`enums.historical_event_type.${dialogDetailsItem.type}`) }}</v-card-title>
        <v-card-text>
          <v-simple-table>
            <tbody>
            <tr v-for="[key, value] in Object.entries(dialogDetailsItem.properties)" :key="key">
              <td class="text-capitalize font-weight-bold">{{ formatPropertyKey(key) }}</td>
              <td>{{ value }}</td>
            </tr>
            <tr v-if="getPageHash(dialogDetailsItem)">
              <td class="font-weight-bold">Page</td>
              <td>
                <v-img
                  width="200"
                  height="300"
                  contain
                  :src="pageHashKnownThumbnailUrl(getPageHash(dialogDetailsItem))"
                />
              </td>
            </tr>
            </tbody>
          </v-simple-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn @click="dialogDetails = false" text>{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts">
import Vue from 'vue'
import {HistoricalEventDto} from '@/types/komga-history'
import {SeriesDto} from '@/types/komga-series'
import {BookDto} from '@/types/komga-books'
import {pageHashKnownThumbnailUrl} from '@/functions/urls'
import {PageHashKnownDto} from '@/types/komga-pagehashes'

export default Vue.extend({
  name: 'HistoryView',
  data: function () {
    return {
      pageHashKnownThumbnailUrl,
      items: [] as HistoricalEventDto[],
      totalElements: 0,
      loading: true,
      options: {} as any,
      dialogDetails: false,
      dialogDetailsItem: undefined as HistoricalEventDto | undefined,
      seriesCache: [] as SeriesDto[],
      seriesCacheNotFound: [] as string[],
      booksCache: [] as BookDto[],
      booksCacheNotFound: [] as string[],
    }
  },
  watch: {
    options: {
      handler() {
        this.loadData()
      },
      deep: true,
    },
  },
  computed: {
    headers(): object[] {
      return [
        {text: this.$t('history.header.type').toString(), value: 'type'},
        {text: this.$t('history.header.series').toString(), value: 'seriesId'},
        {text: this.$t('history.header.book').toString(), value: 'bookId'},
        {text: this.$t('history.header.date').toString(), value: 'timestamp'},
        {text: this.$t('history.header.details').toString(), value: 'properties', sortable: false},
      ]
    },
  },
  methods: {
    getPageHash(item: HistoricalEventDto): PageHashKnownDto | undefined {
      if (item.type !== 'DuplicatePageDeleted') return undefined
      let size: any = item.properties['page file size' as any]
      if (size === 'null') size = -1
      return {
        hash: item.properties['page file hash' as any],
        size: size,
        mediaType: item.properties['page media type' as any],
      } as any
    },
    getSeries(seriesId: string): SeriesDto | undefined {
      return this.seriesCache.find(x => x.id === seriesId)
    },
    getBook(bookId: string): BookDto | undefined {
      return this.booksCache.find(x => x.id === bookId)
    },
    showDetails(item: HistoricalEventDto) {
      this.dialogDetailsItem = item
      this.dialogDetails = true
    },
    getIcon(type: string): string {
      switch (type) {
        case 'BookFileDeleted':
          return 'mdi-file-remove'
        case 'SeriesFolderDeleted':
          return 'mdi-folder-remove'
        case 'DuplicatePageDeleted':
          return 'mdi-book-minus'
        case 'BookConverted':
          return 'mdi-archive-refresh'
        case 'BookImported':
          return 'mdi-import'
        case 'BookPushedToKindleInitialized':
        case 'BookPushedToKindleSuccess':
        case 'BookPushedToKindleFailed':
          return 'mdi-send'
        default:
          return ''
      }
    },
    getEventColor(type: string): string {
      switch (type) {
        case 'BookPushedToKindleInitialized':
          return '' // Default color for initialized
        case 'BookPushedToKindleSuccess':
          return 'green' // Green for success
        case 'BookPushedToKindleFailed':
          return 'red' // Red for failure
        default:
          return ''
      }
    },
    formatPropertyKey(key: string): string {
      // Convert snake_case to Title Case with spaces
      return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    },
    async loadData() {
      this.loading = true

      const {sortBy, sortDesc, page, itemsPerPage} = this.options

      const pageRequest = {
        page: page - 1,
        size: itemsPerPage,
        sort: [],
      } as PageRequest

      for (let i = 0; i < sortBy.length; i++) {
        pageRequest.sort!!.push(`${sortBy[i]},${sortDesc[i] ? 'desc' : 'asc'}`)
      }

      const itemsPage = await this.$komgaHistory.getAll(pageRequest)
      this.totalElements = itemsPage.totalElements
      this.items = itemsPage.content

      for (const seriesId of new Set(this.items.map(x => x.seriesId))) {
        if (seriesId && !this.seriesCacheNotFound.includes(seriesId) && !this.getSeries(seriesId)) {
          this.$komgaSeries.getOneSeries(seriesId)
            .then(s => this.seriesCache.push(s))
            .catch(() => this.seriesCacheNotFound.push(seriesId))
        }
      }

      for (const bookId of new Set(this.items.map(x => x.bookId))) {
        if (bookId && !this.booksCacheNotFound.includes(bookId) && !this.getBook(bookId)) {
          this.$komgaBooks.getBook(bookId)
            .then(b => this.booksCache.push(b))
            .catch(() => this.booksCacheNotFound.push(bookId))
        }
      }

      this.loading = false
    },
  },
})
</script>

<style scoped>

</style>

```
### HistoricalEventDto (Frontend)
```typescript
export interface HistoricalEventDto {
  type: string,
  timestamp: Date,
  bookId?: string,
  seriesId?: string,
  properties: Record<string, string>[],
}
```

### BookPushedToKindleSuccess (Backend - Current)
```kotlin
class BookPushedToKindleSuccess(
  book: Book,
  series: Series,
  kindlePath: String,
) : HistoricalEvent(
  type = "BookPushedToKindleSuccess",
  bookId = book.id,
  seriesId = series.id,
  properties = mapOf(
    "name" to book.path.toString(),
    "series" to series.name,
    "kindle_path" to kindlePath,
  ),
)
```

### BookPushedToKindleSuccess (Backend - Updated)
```kotlin
class BookPushedToKindleSuccess(
  book: Book,
  series: Series,
  kindlePath: String,
  processingTimeSeconds: Long,
) : HistoricalEvent(
  type = "BookPushedToKindleSuccess",
  bookId = book.id,
  seriesId = series.id,
  properties = mapOf(
    "name" to book.path.toString(),
    "series" to series.name,
    "kindle_path" to kindlePath,
    "processing_time_seconds" to processingTimeSeconds.toString(),
  ),
)
```

## 5. Expected Output

### Frontend Display
When users view the history details for a successful Kindle push, they should see:

```
Type: Book pushed to Kindle
Name: /path/to/book.cbz
Series: Series Name
Kindle Path: New Volume
Processing Time: 45 seconds
Timestamp: 2025-01-15 14:30:25
```

### Script Output
The Python script should output processing time in a structured format:
```
HISTORICAL_EVENT_KINDLE_PATH:New Volume
HISTORICAL_EVENT_PROCESSING_TIME:45
SCRIPT_STATUS:SUCCESS
```

### Backend Event Creation
The controller should parse the processing time and create the historical event with the timing information included.

## Implementation Notes

1. **Timing Measurement**: Processing time should be measured from the start of script execution until completion, covering file processing, KCC conversion, and SCP transfer.

2. **Error Handling**: If timing measurement fails, the system should still function normally but without processing time data.

3. **Backward Compatibility**: The changes should be backward compatible. Historical events created without processing time should still display properly.

4. **Unit Formatting**: Processing time should be displayed in seconds with appropriate formatting (e.g., "45 seconds" for times under 60 seconds, "1 minute 5 seconds" for longer times).

5. **Data Validation**: The backend should validate that the processing time is a reasonable number (positive, not excessively large).