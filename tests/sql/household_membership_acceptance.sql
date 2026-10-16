-- Run only against an ephemeral CI PostgreSQL database.
-- The proposed membership migration remains quarantined from live migrations.
DO $saathi_test$
DECLARE
  user_one uuid := gen_random_uuid();
  user_two uuid := gen_random_uuid();
  household_one uuid;
  household_one_repeat uuid;
  household_two uuid;
  pin_one text := repeat('a', 64);
  pin_two text := repeat('b', 64);
  shared_phone text := '+15551234567';
  household_phone text;
  membership_count integer;
BEGIN
  INSERT INTO auth.users (id) VALUES (user_one), (user_two);

  SELECT enrolled.household_id INTO household_one
  FROM public.saathi_enroll_household(user_one, shared_phone, pin_one) AS enrolled;

  SELECT enrolled.household_id INTO household_one_repeat
  FROM public.saathi_enroll_household(user_one, shared_phone, pin_one) AS enrolled;

  IF household_one IS NULL OR household_one_repeat <> household_one THEN
    RAISE EXCEPTION 'test_failed: enrollment must be idempotent for the same identity and PIN';
  END IF;

  BEGIN
    PERFORM 1 FROM public.saathi_enroll_household(user_one, shared_phone, pin_two);
    RAISE EXCEPTION 'test_failed: changing the PIN during enrollment must fail';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'household_pin_already_set' THEN
      RAISE;
    END IF;
  END;

  SELECT enrolled.household_id INTO household_two
  FROM public.saathi_enroll_household(user_two, shared_phone, pin_two) AS enrolled;

  IF household_two IS NULL OR household_two = household_one THEN
    RAISE EXCEPTION 'test_failed: recycled phone must never adopt another household';
  END IF;

  SELECT phone_number INTO household_phone
  FROM public.saathi_households WHERE id = household_two;
  IF household_phone IS NOT NULL THEN
    RAISE EXCEPTION 'test_failed: duplicate verified phone must not be assigned to a second household';
  END IF;

  SELECT count(*) INTO membership_count
  FROM public.saathi_household_memberships WHERE auth_user_id = user_one;
  IF membership_count <> 1 THEN
    RAISE EXCEPTION 'test_failed: concurrent/repeated enrollment must produce one membership';
  END IF;

  IF (SELECT count(*) FROM public.saathi_household_memberships) <> 2 THEN
    RAISE EXCEPTION 'test_failed: expected exactly two distinct memberships';
  END IF;

  BEGIN
    PERFORM * FROM public.saathi_enroll_household(NULL, shared_phone, pin_one);
    RAISE EXCEPTION 'test_failed: null identity must be rejected';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'valid_household_enrollment_input_required' THEN
      RAISE;
    END IF;
  END;
END;
$saathi_test$;
