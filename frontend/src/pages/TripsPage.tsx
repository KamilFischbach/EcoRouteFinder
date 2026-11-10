import { useState } from 'react';

import { getErrorMessage } from '@/api/errors';
import { Card, CardHeader } from '@/components/Card';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { PageHeader } from '@/components/PageHeader';
import { TripForm } from '@/features/trips/TripForm';
import { TripHistory } from '@/features/trips/TripHistory';
import { useCreateTrip, useDeleteTrip, useUpdateTrip } from '@/features/trips/useTrips';
import { toFormValues } from '@/features/trips/validation';
import type { Trip, TripInput } from '@/types/trip';

export function TripsPage() {
  const [editing, setEditing] = useState<Trip | null>(null);
  const [toDelete, setToDelete] = useState<Trip | null>(null);
  // Bumping the key remounts the form, which resets it after a successful save.
  const [formKey, setFormKey] = useState(0);

  const createTrip = useCreateTrip();
  const updateTrip = useUpdateTrip();
  const deleteTrip = useDeleteTrip();
  const activeMutation = editing ? updateTrip : createTrip;

  function resetForm() {
    setEditing(null);
    createTrip.reset();
    updateTrip.reset();
    setFormKey((key) => key + 1);
  }

  function handleSubmit(input: TripInput) {
    if (editing) {
      updateTrip.mutate({ id: editing.id, input }, { onSuccess: resetForm });
    } else {
      createTrip.mutate(input, { onSuccess: resetForm });
    }
  }

  function handleEdit(trip: Trip) {
    createTrip.reset();
    updateTrip.reset();
    setEditing(trip);
    setFormKey((key) => key + 1);
  }

  function handleConfirmDelete() {
    if (!toDelete) return;
    deleteTrip.mutate(toDelete.id, {
      onSuccess: () => {
        if (editing?.id === toDelete.id) resetForm();
        setToDelete(null);
      },
    });
  }

  function handleCancelDelete() {
    setToDelete(null);
    deleteTrip.reset();
  }

  return (
    <>
      <PageHeader
        title="Twoje trasy"
        description="Zapisuj podróże i sprawdzaj, jak wybór środka transportu wpływa na ślad węglowy."
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <Card className="lg:sticky lg:top-24">
          <CardHeader
            title={editing ? 'Edytuj trasę' : 'Nowa trasa'}
            description={
              editing
                ? `${editing.origin} → ${editing.destination}`
                : 'Podaj skąd, dokąd i czym jedziesz.'
            }
          />
          <div className="px-5 py-5 sm:px-6">
            <TripForm
              key={formKey}
              initialValues={editing ? toFormValues(editing) : undefined}
              submitLabel={editing ? 'Zapisz zmiany' : 'Dodaj trasę'}
              isSubmitting={activeMutation.isPending}
              serverError={activeMutation.isError ? getErrorMessage(activeMutation.error) : null}
              onSubmit={handleSubmit}
              onCancel={editing ? resetForm : undefined}
            />
          </div>
        </Card>

        <TripHistory editingId={editing?.id ?? null} onEdit={handleEdit} onDelete={setToDelete} />
      </div>

      <ConfirmDialog
        open={toDelete !== null}
        title="Usunąć trasę?"
        description={
          toDelete
            ? `Trasa ${toDelete.origin} → ${toDelete.destination} zostanie trwale usunięta z historii.`
            : ''
        }
        confirmLabel="Usuń"
        isPending={deleteTrip.isPending}
        error={deleteTrip.isError ? getErrorMessage(deleteTrip.error) : null}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </>
  );
}
