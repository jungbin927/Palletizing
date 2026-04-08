(define (domain pallet_loading)
  (:requirements :strips :typing :negative-preconditions)

  (:types
    box pallet region
  )

  (:predicates
    (arrived ?b - box)
    (box-region ?b - box ?r - region)
    (pallet-region ?p - pallet ?r - region)

    (open ?p - pallet)
    (closed ?p - pallet)

    (assigned ?b - box ?p - pallet)
    (processed ?b - box)
  )

  (:action open-new-pallet
    :parameters (?p - pallet ?r - region)
    :precondition (and
      (closed ?p)
      (pallet-region ?p ?r)
    )
    :effect (and
      (open ?p)
      (not (closed ?p))
    )
  )

  (:action assign-box-to-pallet
    :parameters (?b - box ?p - pallet ?r - region)
    :precondition (and
      (arrived ?b)
      (box-region ?b ?r)
      (pallet-region ?p ?r)
      (open ?p)
      (not (processed ?b))
    )
    :effect (and
      (assigned ?b ?p)
      (processed ?b)
    )
  )

  (:action close-pallet
    :parameters (?p - pallet)
    :precondition (open ?p)
    :effect (and
      (closed ?p)
      (not (open ?p))
    )
  )
)